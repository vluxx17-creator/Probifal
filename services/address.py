import aiohttp
import json
from config import Config
from redis_client import get_cache, set_cache

async def address_lookup(address: str) -> dict:
    cache_key = f"address:{address}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    if Config.USE_NOMINATIM:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        headers = {"User-Agent": "ProbifAmBot/1.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data:
                    item = data[0]
                    addr = item.get("address", {})
                    result = {
                        "address": item.get("display_name"),
                        "coordinates": {"lon": item.get("lon"), "lat": item.get("lat")},
                        "city": addr.get("city") or addr.get("town") or addr.get("village"),
                        "country": addr.get("country"),
                        "postcode": addr.get("postcode")
                    }
                else:
                    result = {"error": "Адрес не найден"}
    else:
        # Если есть Яндекс-ключ
        if Config.YANDEX_GEO_KEY:
            url = "https://geocode-maps.yandex.ru/1.x/"
            params = {
                "apikey": Config.YANDEX_GEO_KEY,
                "geocode": address,
                "format": "json",
                "results": 1
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    data = await resp.json()
                    try:
                        geo = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                        pos = geo["Point"]["pos"].split()
                        result = {
                            "address": geo["metaDataProperty"]["GeocoderMetaData"]["Address"]["formatted"],
                            "coordinates": {"lon": pos[0], "lat": pos[1]},
                            "kind": geo["metaDataProperty"]["GeocoderMetaData"]["kind"],
                            "postal_code": geo["metaDataProperty"]["GeocoderMetaData"]["Address"].get("postal_code")
                        }
                    except (KeyError, IndexError):
                        result = {"error": "Адрес не найден"}
        else:
            result = {"error": "Не настроен геокодер. Установите USE_NOMINATIM=True или добавьте YANDEX_GEO_KEY"}
    
    await set_cache(cache_key, json.dumps(result))
    return result
