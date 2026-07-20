import aiohttp
import json
import re
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from redis_client import get_cache, set_cache
from config import Config

logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
async def phone_lookup(phone: str) -> dict:
    # Оставляем только цифры (убираем +, пробелы, скобки, тире)
    clean_phone = re.sub(r'\D', '', phone)
    if not clean_phone:
        return {"error": "Номер не содержит цифр"}
    
    # Если номер начинается с 8, заменяем на 7 (для России)
    if clean_phone.startswith('8'):
        clean_phone = '7' + clean_phone[1:]
    
    # Если номер не начинается с 7 или 1 (международный), добавляем код страны по умолчанию?
    # Для AbstractAPI нужно передавать номер в международном формате без +
    # Например, для России: 79001234567
    # Если номер короткий, возможно, нужно добавить код страны 7
    if len(clean_phone) == 10 and clean_phone.startswith('9'):
        clean_phone = '7' + clean_phone
    elif len(clean_phone) == 11 and clean_phone.startswith('7'):
        pass  # уже нормально
    else:
        # Оставляем как есть, но API может не распознать
        pass
    
    cache_key = f"phone:{clean_phone}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    if not Config.PHONE_API_KEY:
        result = {"error": "PHONE_API_KEY не задан в .env"}
        await set_cache(cache_key, json.dumps(result), ttl=60)
        return result

    url = "https://phonevalidation.abstractapi.com/v1/"
    params = {
        "api_key": Config.PHONE_API_KEY,
        "phone": clean_phone   # <-- передаём только цифры
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                logger.info(f"AbstractAPI ответ для {clean_phone}: {data}")
                if data.get("valid"):
                    result = {
                        "phone": data.get("phone", {}).get("number", phone),
                        "country": data.get("country", {}).get("name"),
                        "country_code": data.get("country", {}).get("code"),
                        "region": data.get("location", ""),
                        "carrier": data.get("carrier", ""),
                        "line_type": data.get("line_type", ""),
                        "is_valid": data.get("valid", False),
                        "international_format": data.get("phone", {}).get("international"),
                        "national_format": data.get("phone", {}).get("national"),
                        "e164_format": data.get("phone", {}).get("e164"),
                        "location": data.get("location", ""),
                        "timezone": data.get("timezone", ""),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "is_possible": data.get("possible", False),
                        "is_risky": data.get("risky", False)
                    }
                else:
                    # Расшифровываем причину
                    error_msg = data.get("error", {}).get("message") or "Номер невалидный или не найден в базе"
                    result = {"error": f"API вернул: {error_msg}"}
    except Exception as e:
        logger.exception("Ошибка запроса к AbstractAPI")
        result = {"error": f"Ошибка HTTP-запроса: {str(e)}"}
    
    await set_cache(cache_key, json.dumps(result))
    return result
