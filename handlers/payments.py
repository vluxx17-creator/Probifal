from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, PreCheckoutQueryHandler
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
        # Формируем инвойс
        title = f"Пакет {req_count} запросов"
        description = f"Пополнение баланса на {req_count} запросов в ProbifAm"
        payload = f"package_{req_count}_{price_stars}"
        prices = [LabeledPrice(label=title, amount=price_stars)]  # amount в звёздах
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # для Stars не требуется
            currency="XTR",
            prices=prices,
            start_parameter="probifam_payment"
        )

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    # Можно проверить сумму или payload
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = update.message.successful_payment.payload
    parts = payload.split("_")
    req_count = int(parts[1])
    price_stars = int(parts[2])
    user_id = update.effective_user.id
    # Начисляем запросы
    await add_balance(user_id, req_count)
    # Запись покупки
    async with AsyncSessionLocal() as session:
        purchase = Purchase(
            user_id=user_id,
            amount_requests=req_count,
            price_stars=price_stars,
            status="completed"
        )
        session.add(purchase)
        await session.commit()
    await update.message.reply_text(
        f"✅ Оплата прошла успешно! На ваш баланс добавлено {req_count} запросов."
    )
