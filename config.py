import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    VK_TOKEN = os.getenv("VK_TOKEN", "")
    YANDEX_GEO_KEY = os.getenv("YANDEX_GEO_KEY", "")
    USE_NOMINATIM = os.getenv("USE_NOMINATIM", "False").lower() == "true"
    
    # Цены (запросы -> звёзды)
    PRICE_MAP = {
        15: 64,
        30: 116,
        300: 800,
        1000: 2560,
        3000: 7680,
        10000: 18400,
    }
    FREE_TRIALS_PER_TYPE = 2
    REQUEST_TYPES = ("phone", "ip", "address", "vk")
    CACHE_TTL = 86400  # кеш в памяти, если нет Redis
    DATABASE_URL = "sqlite+aiosqlite:///probifam.db"  # SQLite
