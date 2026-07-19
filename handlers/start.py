from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
from database import AsyncSessionLocal
from models import User
from datetime import datetime
from sqlalchemy import select

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == user.id)
        db_user = await session.execute(stmt)
        db_user = db_user.scalar_one_or_none()
        if not db_user:
            new_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                is_admin=(user.id in Config.ADMIN_IDS),
                free_requests={t: Config.FREE_TRIALS_PER_TYPE for t in Config.REQUEST_TYPES}
            )
            session.add(new_user)
            await session.commit()
    
    keyboard = [
        [InlineKeyboardButton("🔍 Пробив по номеру", callback_data="phone")],
        [InlineKeyboardButton("🌐 Пробив по IP/домену", callback_data="ip")],
        [InlineKeyboardButton("📍 Пробив по адресу", callback_data="address")],
        [InlineKeyboardButton("🎯 Пробив по VK", callback_data="vk")],
        [InlineKeyboardButton("📊 Мои запросы", callback_data="balance")],
        [InlineKeyboardButton("💰 Купить звёзды", callback_data="buy")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")],
        [InlineKeyboardButton("📟 Мой IP", callback_data="myip")],
    ]
    if user.id in Config.ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Добро пожаловать в ProbifAm — сервис проверки данных.\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )
