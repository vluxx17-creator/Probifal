import aiohttp
import json
from config import Config
from redis_client import get_cache, set_cache

async def vk_lookup(query: str) -> dict:
    cache_key = f"vk:{query}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    # Если query похожа на ссылку – извлекаем screen_name
    if "vk.com/" in query:
        screen_name = query.split("/")[-1].split("?")[0]
    else:
        screen_name = query  # предполагаем, что это уже id или короткое имя
    
    url = "https://api.vk.com/method/users.get"
    params = {
        "user_ids": screen_name,
        "fields": "photo_200,city,status,last_seen,country",
        "access_token": Config.VK_TOKEN,
        "v": "5.131"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            if "response" in data and data["response"]:
                user = data["response"][0]
                result = {
                    "id": user["id"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "is_closed": user.get("is_closed", False),
                    "can_access_closed": user.get("can_access_closed", False),
                    "photo": user.get("photo_200", ""),
                    "city": user.get("city", {}).get("title") if user.get("city") else None,
                    "country": user.get("country", {}).get("title") if user.get("country") else None,
                    "status": user.get("status", ""),
                    "last_seen": user.get("last_seen", {}).get("time") if user.get("last_seen") else None
                }
            else:
                result = {"error": "Пользователь не найден или профиль закрыт"}
            await set_cache(cache_key, json.dumps(result), ttl=3600)
            return result
