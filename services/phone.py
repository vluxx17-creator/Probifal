import aiohttp
import json
import re
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from redis_client import get_cache, set_cache
from config import Config

logger = logging.getLogger(__name__)

# --- PhoneInfoga ---
async def phone_lookup_phoneinfoga(phone: str) -> dict:
    """Запрос к PhoneInfoga API (если развёрнут)"""
    clean_phone = re.sub(r'\D', '', phone)
    if not clean_phone:
        return {"error": "Номер не содержит цифр"}
    
    if not phone.startswith('+'):
        phone = '+' + clean_phone
    
    cache_key = f"phoneinfoga:{phone}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    try:
        url = f"{Config.PHONEINFOGA_API_URL}/api/v2/scan"
        params = {"number": phone}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as resp:
                if resp.status != 200:
                    return {"error": f"PhoneInfoga ошибка {resp.status}"}
                data = await resp.json()
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
                await set_cache(cache_key, json.dumps(result), ttl=3600)
                return result
    except Exception as e:
        logger.warning(f"PhoneInfoga недоступен: {e}")
        return {"error": f"PhoneInfoga: {str(e)}"}

# --- Numverify ---
async def phone_lookup_numverify(phone: str) -> dict:
    """Запрос к Numverify API (основной)"""
    clean_phone = re.sub(r'\D', '', phone)
    if not clean_phone:
        return {"error": "Номер не содержит цифр"}
    
    # Numverify требует номер без "+", только цифры
    cache_key = f"numverify:{clean_phone}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    if not Config.NUMVERIFY_API_KEY:
        return {"error": "NUMVERIFY_API_KEY не задан"}
    
    url = "http://apilayer.net/api/validate"
    params = {
        "access_key": Config.NUMVERIFY_API_KEY,
        "number": clean_phone,
        "format": 1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                logger.info(f"Numverify ответ для {clean_phone}: {data}")
                if data.get("valid"):
                    result = {
                        "phone": clean_phone,
                        "country": data.get("country_name"),
                        "country_code": data.get("country_code"),
                        "region": data.get("location", ""),
                        "carrier": data.get("carrier", ""),
                        "line_type": data.get("line_type", ""),
                        "is_valid": data.get("valid", False),
                        "international_format": data.get("international_format"),
                        "national_format": data.get("national_format"),
                        "location": data.get("location", ""),
                        "timezone": data.get("timezone", ""),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "is_possible": True,
                        "is_risky": False
                    }
                else:
                    error_msg = data.get("error", {}).get("info") or "Номер невалидный"
                    result = {"error": f"Numverify: {error_msg}"}
                await set_cache(cache_key, json.dumps(result), ttl=86400)
                return result
    except Exception as e:
        logger.exception("Ошибка Numverify")
        return {"error": f"Numverify: {str(e)}"}

# --- AbstractAPI (резерв) ---
async def phone_lookup_abstract(phone: str) -> dict:
    """Запрос к AbstractAPI (резервный)"""
    clean_phone = re.sub(r'\D', '', phone)
    if not clean_phone:
        return {"error": "Номер не содержит цифр"}
    
    if clean_phone.startswith('8'):
        clean_phone = '7' + clean_phone[1:]
    if len(clean_phone) == 10 and clean_phone.startswith('9'):
        clean_phone = '7' + clean_phone
    
    cache_key = f"abstract:{clean_phone}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    if not Config.PHONE_API_KEY:
        return {"error": "PHONE_API_KEY не задан"}
    
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
                    result = {"error": f"AbstractAPI: {data.get('error', {}).get('message', 'невалидный')}"}
                await set_cache(cache_key, json.dumps(result))
                return result
    except Exception as e:
        return {"error": f"AbstractAPI: {str(e)}"}

# --- Основная функция ---
async def phone_lookup(phone: str) -> dict:
    """Главная функция: PhoneInfoga → Numverify → AbstractAPI"""
    # 1. Пробуем PhoneInfoga
    pi_result = await phone_lookup_phoneinfoga(phone)
    if not pi_result.get("error") and pi_result.get("carrier"):
        # Если PhoneInfoga дал оператора, считаем его успешным
        return pi_result
    
    # 2. Пробуем Numverify
    nv_result = await phone_lookup_numverify(phone)
    if not nv_result.get("error") and nv_result.get("carrier"):
        # Если есть данные от Numverify, добавляем следы от PhoneInfoga (если были)
        if pi_result.get("footprints"):
            nv_result["footprints"] = pi_result["footprints"]
        if pi_result.get("owner_hints"):
            nv_result["owner_hints"] = pi_result["owner_hints"]
        return nv_result
    
    # 3. Пробуем AbstractAPI как резерв
    ab_result = await phone_lookup_abstract(phone)
    if not ab_result.get("error"):
        if pi_result.get("footprints"):
            ab_result["footprints"] = pi_result["footprints"]
        if pi_result.get("owner_hints"):
            ab_result["owner_hints"] = pi_result["owner_hints"]
        return ab_result
    
    # 4. Если всё сломалось – возвращаем ошибку
    return {"error": "Все API недоступны или ключи невалидны"}
