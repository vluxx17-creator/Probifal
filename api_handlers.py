import aiohttp
import whois
import json
from vk_api import VkApi
from vk_api.exceptions import ApiError
import config
import html

async def search_vk_by_name(name):
    try:
        vk_session = VkApi(token=config.VK_TOKEN)
        vk = vk_session.get_api()
        users = vk.users.search(q=name, count=10, fields="city,country,bdate,photo_max,sex,last_seen")
        result = []
        for u in users.get('items', []):
            result.append({
                "id": u.get("id"),
                "first_name": u.get("first_name"),
                "last_name": u.get("last_name"),
                "city": u.get("city", {}).get("title") if u.get("city") else None,
                "country": u.get("country", {}).get("title") if u.get("country") else None,
                "bdate": u.get("bdate"),
                "sex": "мужской" if u.get("sex") == 2 else "женский" if u.get("sex") == 1 else "не указан",
                "photo": u.get("photo_max"),
                "last_seen": u.get("last_seen", {}).get("time") if u.get("last_seen") else None
            })
        return result
    except ApiError as e:
        error_code = e.error.get('error_code')
        error_msg = e.error.get('error_msg')
        if error_code == 5:
            return {"error": "Неверный или истёкший токен VK."}
        elif error_code == 6:
            return {"error": "Слишком много запросов к VK API."}
        else:
            return {"error": f"VK API error {error_code}: {error_msg}"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

async def search_by_ip(ip):
    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    return data
                else:
                    return {"error": data.get("message", "Unknown error")}
    except Exception as e:
        return {"error": str(e)}

async def search_by_domain(domain):
    try:
        w = whois.whois(domain)
        return {
            "domain_name": str(w.domain_name) if w.domain_name else None,
            "registrar": str(w.registrar) if w.registrar else None,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "name_servers": w.name_servers if w.name_servers else [],
            "emails": w.emails if w.emails else []
        }
    except Exception as e:
        return {"error": str(e)}

async def search_by_nick(nick):
    results = {}
    # GitHub
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/users/{nick}", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results["github"] = data.get("html_url")
                else:
                    results["github"] = None
    except:
        results["github"] = None

    # VK
    vk_data = await search_vk_by_name(nick)
    if isinstance(vk_data, list) and len(vk_data) > 0:
        results["vk"] = [{"id": u["id"], "name": f"{u['first_name']} {u['last_name']}"} for u in vk_data[:3]]
    else:
        results["vk"] = None

    # Другие платформы
    for platform, url in [("telegram", f"https://t.me/{nick}"), 
                          ("twitter", f"https://twitter.com/{nick}"),
                          ("instagram", f"https://instagram.com/{nick}")]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10, allow_redirects=False) as resp:
                    results[platform] = url if resp.status == 200 else None
        except:
            results[platform] = None
    return results

async def search_by_phone(phone):
    """
    Реальный поиск по номеру телефона:
    - Оператор через numverify
    - Поиск в VK по номеру (через users.search с текстом номера)
    - Проверка наличия в открытых профилях (Instagram, Telegram) — через HTTP-запросы
    """
    result = {}
    phone_clean = ''.join(filter(str.isdigit, phone))

    # 1. Оператор через numverify
    if config.NUMVERIFY_API_KEY:
        try:
            url = f"http://apilayer.net/api/validate?access_key={config.NUMVERIFY_API_KEY}&number={phone}&country_code=&format=1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    data = await resp.json()
                    if data.get("valid"):
                        result["оператор"] = data.get("carrier")
                        result["страна"] = data.get("country_name")
                        result["регион"] = data.get("location")
                        result["тип_линии"] = data.get("line_type")
                    else:
                        result["оператор"] = "Не определён"
        except:
            result["оператор"] = "Ошибка API"
    else:
        result["оператор"] = "Ключ не задан"

    # 2. Поиск в VK по номеру (как текстовый запрос)
    try:
        vk_session = VkApi(token=config.VK_TOKEN)
        vk = vk_session.get_api()
        # Ищем пользователей, у которых в профиле указан этот номер (редко, но бывает)
        vk_result = vk.users.search(q=phone, count=5, fields="city,country,photo_max")
        if vk_result.get('items'):
            users = []
            for u in vk_result['items']:
                users.append({
                    "id": u.get("id"),
                    "name": f"{u.get('first_name')} {u.get('last_name')}",
                    "city": u.get("city", {}).get("title") if u.get("city") else None,
                    "photo": u.get("photo_max")
                })
            result["vk"] = users
        else:
            result["vk"] = None
    except Exception as e:
        result["vk"] = {"error": str(e)}

    # 3. Проверка Instagram — номер может быть указан в bio, но не гарантировано
    # Пытаемся найти профиль по номеру (нестандартно, но иногда номер в username)
    # Для демонстрации используем проверку существования страницы с номером как username
    insta_url = f"https://instagram.com/{phone_clean}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(insta_url, timeout=10, allow_redirects=False) as resp:
                if resp.status == 200:
                    result["instagram"] = insta_url
                else:
                    result["instagram"] = None
    except:
        result["instagram"] = None

    # 4. Telegram — номер не является username, поэтому проверяем только если номер совпадает с username (редко)
    tg_url = f"https://t.me/{phone_clean}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(tg_url, timeout=10, allow_redirects=False) as resp:
                if resp.status == 200:
                    result["telegram"] = tg_url
                else:
                    result["telegram"] = None
    except:
        result["telegram"] = None

    # 5. GitHub — номер не используется
    result["github"] = None

    # 6. Если ничего не найдено — явно указываем
    if not any([result.get("vk"), result.get("instagram"), result.get("telegram"), result.get("github")]):
        result["соцсети"] = "Не найдены"

    return result
