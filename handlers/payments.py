from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes
from config import Config
from utils.balance import add_balance
from database import AsyncSessionLocal
from models import Purchase

def build_packages_keyboard():
    keyboard = []
    for req, price in Config.PRICE_MAP.items():
        keyboard.append([InlineKeyboardButton(
            f"{req} запросов — {price} ⭐",
            callback_data=f"buy_{req}_{price}"
        )])
    return InlineKeyboardMarkup(keyboard)

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("buy_"):
        parts = data.split("_")
        req_count = int(parts[1])
        price_stars = int(parts[2])
        # В реальности здесь должен быть send_invoice, но для теста просто начисляем
        # (имитация покупки)
        await add_balance(update.effective_user.id, req_count)
        async with AsyncSessionLocal() as session:
            purchase = Purchase(
                user_id=update.effective_user.id,
                amount_requests=req_count,
                price_stars=price_stars,
                status="completed"
            )
            session.add(purchase)
            await session.commit()
        await query.edit_message_text(
            f"✅ Пополнение на {req_count} запросов выполнено (имитация).\n"
            f"Списано {price_stars} звёзд (в реальности — через Telegram Stars)."
        )
