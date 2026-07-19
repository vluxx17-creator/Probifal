# Простой кеш в памяти, чтобы не требовать Redis
_cache = {}

async def get_cache(key: str):
    return _cache.get(key)

async def set_cache(key: str, value: str, ttl: int = 86400):
    _cache[key] = value

async def delete_cache(key: str):
    _cache.pop(key, None)
