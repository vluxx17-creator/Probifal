import aiohttp
import json
import re
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from redis_client import get_cache, set_cache
from config import Config

logger = logging.getLogger(__name__)

# Адрес PhoneInfoga API (из конфига)
PHONEINFOGA_API_URL = Config.PHONEINFOGA_API_URL

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=3))
async def phone_lookup_phoneinfoga(phone: str) -> dict:
    """Запрос к PhoneInfoga API"""
    clean_phone = re.sub(r'\D', '', phone)
    if not clean_phone:
        return {"error": "Номер не содержит цифр"}
    
    # PhoneInfoga принимает номер с +
    if not phone.startswith('+'):
        phone = '+' + clean_phone
    
    cache_key = f"phoneinfoga:{phone}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    try:
        # PhoneInfoga API v2 — эндпоинт /api/v2/scan
        url = f"{PHONEINFOGA_API_URL}/api/v2/scan"
        params = {"number": phone}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return {"error": f"PhoneInfoga API вернул ошибку {resp.status}"}
                
                data = await resp.json()
                
                # Парсим ответ PhoneInfoga
                result = {
                    "phone": phone,
                    "country": data.get("country", {}).get("name"),
                    "country_code": data.get("country", {}).get("code"),
                    "region": data.get("area", ""),
                    "carrier": data.get("carrier", ""),
                    "line_type": data.get("line_type", ""),
                    "is_valid": data.get("valid", False),
                    "international_format": data.get("international", phone),
                    "national_format": data.get("national", phone),
                    "location": data.get("location", ""),
                }
                
                # 🔥 Ищем следы (footprints) – там может быть имя владельца
                footprints = data.get("footprints", [])
                if footprints:
                    footprint_links = []
                    owner_hints = []
                    for fp in footprints:
                        if isinstance(fp, dict):
                            url_fp = fp.get("url", "")
                            title = fp.get("title", "")
                            if url_fp:
                                footprint_links.append(url_fp)
                            if title and len(title) < 50:
                                owner_hints.append(title)
                        elif isinstance(fp, str) and fp.startswith("http"):
                            footprint_links.append(fp)
                    
                    result["footprints"] = footprint_links[:10]
                    if owner_hints:
                        result["owner_hints"] = list(set(owner_hints))[:5]
                
                # Если есть данные от Numverify (если ключ настроен в PhoneInfoga)
                if "numverify" in data:
                    nv = data["numverify"]
                    result["carrier"] = nv.get("carrier", result.get("carrier"))
                    result["line_type"] = nv.get("line_type", result.get("line_type"))
                    result["country"] = nv.get("country_name", result.get("country"))
                
                await set_cache(cache_key, json.dumps(result), ttl=3600)
                return result
                
    except aiohttp.ClientError as e:
        logger.error(f"PhoneInfoga API недоступен: {e}")
        return {"error": f"PhoneInfoga API недоступен: {str(e)}"}
    except Exception as e:
        logger.exception("Ошибка при запросе к PhoneInfoga")
        return {"error": f"Ошибка: {str(e)}"}


async def phone_lookup(phone: str) -> dict:
    """Основная функция — сначала PhoneInfoga, потом AbstractAPI как резерв"""
    # Сначала пробуем PhoneInfoga
    result = await phone_lookup_phoneinfoga(phone)
    
    # Если PhoneInfoga вернул ошибку или не нашёл данных — пробуем AbstractAPI
    if result.get("error") or not result.get("carrier"):
        logger.info(f"PhoneInfoga не дал результата для {phone}, пробуем AbstractAPI")
        
        # Старый код с AbstractAPI (используем ваш ключ)
        clean_phone = re.sub(r'\D', '', phone)
        if not clean_phone:
            return {"error": "Номер не содержит цифр"}
        
        if clean_phone.startswith('8'):
            clean_phone = '7' + clean_phone[1:]
        
        if len(clean_phone) == 10 and clean_phone.startswith('9'):
            clean_phone = '7' + clean_phone
        
        cache_key = f"phone:{clean_phone}"
        cached = await get_cache(cache_key)
        if cached:
            return json.loads(cached)
        
        if not Config.PHONE_API_KEY:
            # Если нет ключа AbstractAPI, возвращаем то, что дал PhoneInfoga
            return result
        
        url = "https://phonevalidation.abstractapi.com/v1/"
        params = {
            "api_key": Config.PHONE_API_KEY,
            "phone": clean_phone
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    data = await resp.json()
                    if data.get("valid"):
                        abstract_result = {
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
                        # Объединяем с результатами PhoneInfoga (если там были footprints)
                        if result.get("footprints"):
                            abstract_result["footprints"] = result["footprints"]
                        if result.get("owner_hints"):
                            abstract_result["owner_hints"] = result["owner_hints"]
                        await set_cache(cache_key, json.dumps(abstract_result))
                        return abstract_result
                    else:
                        error_msg = data.get("error", {}).get("message") or "Номер невалидный"
                        return {"error": f"AbstractAPI: {error_msg}"}
        except Exception as e:
            logger.exception("Ошибка AbstractAPI")
            return {"error": f"Ошибка AbstractAPI: {str(e)}"}
    
    return result
