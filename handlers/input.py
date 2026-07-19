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

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    awaiting = context.user_data.get("awaiting")
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
            ip_address="0.0.0.0"  # будет заменено, если есть вебхук
        )
        session.add(log_entry)
        await session.commit()
    
    # Форматируем ответ
    if "error" in result:
        answer = f"❌ {result['error']}"
    else:
        lines = []
        for k, v in result.items():
            if v is not None and v != "":
                lines.append(f"• *{k}*: {v}")
        answer = "📋 *Результат пробива:*\n" + "\n".join(lines)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]]
    await update.message.reply_text(answer, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["awaiting"] = None
