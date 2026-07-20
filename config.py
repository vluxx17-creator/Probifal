import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    VK_TOKEN = os.getenv("VK_TOKEN", "")
    YANDEX_GEO_KEY = os.getenv("YANDEX_GEO_KEY", "")
    USE_NOMINATIM = os.getenv("USE_NOMINATIM", "False").lower() == "true"
    PHONE_API_KEY = os.getenv("PHONE_API_KEY", "")
    NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "")  # <-- добавлено
    PHONEINFOGA_API_URL = os.getenv("PHONEINFOGA_API_URL", "http://localhost:5000")
    
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
    CACHE_TTL = 86400
    DATABASE_URL = "sqlite+aiosqlite:///probifam.db"
