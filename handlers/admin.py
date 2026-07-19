from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
from database import AsyncSessionLocal
from models import RequestLog, User, IpLog
from sqlalchemy import select, desc, func, update

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in Config.ADMIN_IDS:
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    keyboard = [
        [InlineKeyboardButton("📋 Логи запросов", callback_data="admin_logs")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📟 Логи IP", callback_data="admin_iplogs")],
        [InlineKeyboardButton("🎁 Выдать админку", callback_data="admin_grant")],
        [InlineKeyboardButton("💎 Выдать запросы", callback_data="admin_add_balance")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    await query.edit_message_text("⚙️ *Админ-панель*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("Введите ID пользователя (число), которому хотите выдать права администратора:")
    context.user_data["admin_action"] = "grant_admin"

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("Введите ID пользователя и количество запросов через пробел (например: 123456789 50):")
    context.user_data["admin_action"] = "add_balance"

async def admin_handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Этот обработчик будет ловить текстовые ответы после нажатия кнопок выдачи
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if user_id not in Config.ADMIN_IDS:
        await update.message.reply_text("❌ Вы не администратор.")
        return
    
    action = context.user_data.get("admin_action")
    if action == "grant_admin":
        try:
            target_id = int(text)
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.telegram_id == target_id)
                user = await session.execute(stmt)
                user = user.scalar_one_or_none()
                if not user:
                    await update.message.reply_text("❌ Пользователь с таким ID не найден.")
                    return
                user.is_admin = True
                await session.commit()
                await update.message.reply_text(f"✅ Пользователь {target_id} теперь администратор.")
        except ValueError:
            await update.message.reply_text("❌ Введите корректный числовой ID.")
    elif action == "add_balance":
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Введите ID и количество через пробел.")
            return
        try:
            target_id = int(parts[0])
            amount = int(parts[1])
            if amount <= 0:
                await update.message.reply_text("❌ Количество должно быть положительным.")
                return
            async with AsyncSessionLocal() as session:
                stmt = select(User).where(User.telegram_id == target_id)
                user = await session.execute(stmt)
                user = user.scalar_one_or_none()
                if not user:
                    await update.message.reply_text("❌ Пользователь с таким ID не найден.")
                    return
                user.balance += amount
                await session.commit()
                await update.message.reply_text(f"✅ Пользователю {target_id} начислено {amount} запросов.")
        except ValueError:
            await update.message.reply_text("❌ Введите корректные числа.")
    else:
        await update.message.reply_text("Неизвестная команда.")
    context.user_data["admin_action"] = None
