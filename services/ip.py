import aiohttp
import json
import whois
from redis_client import get_cache, set_cache

async def ip_lookup(ip: str) -> dict:
    cache_key = f"ip:{ip}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as,query"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as resp:
            data = await resp.json()
            if data.get("status") == "success":
                result = {
                    "ip": data["query"],
                    "country": data["country"],
                    "region": data["regionName"],
                    "city": data["city"],
                    "isp": data["isp"],
                    "org": data["org"],
                    "as": data["as"]
                }
            else:
                result = {"error": "Не удалось определить геолокацию"}
            await set_cache(cache_key, json.dumps(result))
            return result

async def domain_lookup(domain: str) -> dict:
    cache_key = f"domain:{domain}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    try:
        w = whois.whois(domain)
        result = {
            "domain": domain,
            "registrar": w.registrar,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "name_servers": w.name_servers,
            "emails": w.emails,
            "dnssec": w.dnssec
        }
    except Exception as e:
        result = {"error": f"WHOIS ошибка: {str(e)}"}
    
    await set_cache(cache_key, json.dumps(result))
    return result
