import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.phone import phone_lookup
from services.ip import ip_lookup, domain_lookup
from services.address import address_lookup
from services.vk import vk_lookup
from database import AsyncSessionLocal
from models import RequestLog
import json
from datetime import datetime

logger = logging.getLogger(__name__)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если установлен admin_action – передаём управление админ-обработчику
    if context.user_data.get("admin_action"):
        from handlers.admin import admin_handle_input
        await admin_handle_input(update, context)
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()
    awaiting = context.user_data.get("awaiting")
    
    logger.info(f"Получен текст от {user_id}: '{text}', awaiting='{awaiting}'")
    
    if not awaiting:
        await update.message.reply_text("Используйте кнопки в меню. /start")
        return
    
    result = None
    req_type = None
    if awaiting == "phone_input":
        result = await phone_lookup(text)
        req_type = "phone"
    elif awaiting == "ip_input":
        if any(c.isalpha() for c in text):
            result = await domain_lookup(text)
        else:
            result = await ip_lookup(text)
        req_type = "ip"
    elif awaiting == "address_input":
        result = await address_lookup(text)
        req_type = "address"
    elif awaiting == "vk_input":
        result = await vk_lookup(text)
        req_type = "vk"
    else:
        await update.message.reply_text("Неизвестный режим ввода. /start")
        return
    
    # Логируем запрос
    async with AsyncSessionLocal() as session:
        log_entry = RequestLog(
            user_id=user_id,
            request_type=req_type,
            input_data=text,
            response_summary=result,
            ip_address="0.0.0.0"
        )
        session.add(log_entry)
        await session.commit()
    
    # Форматируем ответ с максимальной детализацией
    if "error" in result:
        answer = f"❌ *Ошибка:* {result['error']}"
    else:
        lines = []
        lines.append(f"📋 *Результат пробива по {req_type.upper()}*")
        lines.append("")
        for key, value in result.items():
            if value is None or value == "":
                continue
            # Словарь меток с добавлением новых полей
            label = {
                "phone": "📞 Номер",
                "country": "🌍 Страна",
                "country_code": "🏷 Код страны",
                "region": "🗺 Регион",
                "city": "🏙 Город",
                "carrier": "📶 Оператор",
                "line_type": "📱 Тип линии",
                "is_valid": "✅ Валидность",
                "international_format": "🌐 Международный формат",
                "national_format": "🇷🇺 Национальный формат",
                "e164_format": "🔢 E.164 формат",
                "location": "📍 Местоположение",
                "timezone": "🕒 Часовой пояс",
                "latitude": "🧭 Широта",
                "longitude": "🧭 Долгота",
                "is_possible": "🔮 Возможен",
                "is_risky": "⚠️ Риск",
                "operator_info": "📡 Информация об операторе",
                "region_code": "📌 Код региона",
                "postal_code": "✉️ Почтовый индекс",
                "area_code": "📞 Код города",
                "ip": "🌐 IP-адрес",
                "isp": "🏢 Провайдер",
                "org": "🏛 Организация",
                "as": "🔢 AS",
                "domain": "🌐 Домен",
                "registrar": "📋 Регистратор",
                "creation_date": "📅 Дата создания",
                "expiration_date": "⏳ Дата истечения",
                "name_servers": "📡 DNS-серверы",
                "emails": "📧 Электронная почта",
                "dnssec": "🔒 DNSSEC",
                "address": "🏠 Адрес",
                "coordinates": "🗺 Координаты",
                "postcode": "✉️ Почтовый индекс",
                "first_name": "👤 Имя",
                "last_name": "👤 Фамилия",
                "is_closed": "🔒 Профиль закрыт",
                "can_access_closed": "🔓 Доступ к закрытому",
                "photo": "🖼 Фото",
                "status": "📝 Статус",
                "last_seen": "🕒 Последний визит",
                "footprints": "🔗 Цифровые следы",
                "owner_hints": "👤 Возможный владелец (по следам)"
            }.get(key, key)
            
            if isinstance(value, bool):
                value = "✅ Да" if value else "❌ Нет"
            elif isinstance(value, list):
                if value:
                    if key == "footprints":
                        value = "\n".join([f"  • {url}" for url in value[:5]])
                    else:
                        value = ", ".join(str(v) for v in value[:5])
                else:
                    continue
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            lines.append(f"*{label}:* {value}")
        answer = "\n".join(lines)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]]
    await update.message.reply_text(answer, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["awaiting"] = None
