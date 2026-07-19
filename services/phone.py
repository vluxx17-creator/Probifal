import aiohttp
import json
from tenacity import retry, stop_after_attempt, wait_exponential
from redis_client import get_cache, set_cache
from config import Config

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
async def phone_lookup(phone: str) -> dict:
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    cache_key = f"phone:{phone}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    # Если ключ не задан – выдаём ошибку (чтобы не было заглушек)
    if not Config.PHONE_API_KEY:
        result = {"error": "PHONE_API_KEY не задан в .env. Получите ключ на abstractapi.com"}
        await set_cache(cache_key, json.dumps(result), ttl=60)
        return result

    url = "https://phonevalidation.abstractapi.com/v1/"
    params = {
        "api_key": Config.PHONE_API_KEY,
        "phone": phone
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
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
                    result = {"error": "Номер невалидный или не найден в базе"}
    except Exception as e:
        result = {"error": f"Ошибка HTTP-запроса к API: {str(e)}"}
    
    await set_cache(cache_key, json.dumps(result))
    return result
