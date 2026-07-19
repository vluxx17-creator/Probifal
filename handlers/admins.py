from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
from database import AsyncSessionLocal
from models import RequestLog, User, IpLog
from sqlalchemy import select, desc, func

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != Config.ADMIN_ID:
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    keyboard = [
        [InlineKeyboardButton("📋 Логи запросов", callback_data="admin_logs")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📟 Логи IP", callback_data="admin_iplogs")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    await query.edit_message_text("⚙️ *Админ-панель*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with AsyncSessionLocal() as session:
        stmt = select(RequestLog).order_by(desc(RequestLog.timestamp)).limit(50)
        logs = await session.execute(stmt)
        logs = logs.scalars().all()
        if not logs:
            text = "Логов нет."
        else:
            lines = []
            for log in logs:
                lines.append(
                    f"🕒 {log.timestamp.strftime('%Y-%m-%d %H:%M')} | {log.request_type} | "
                    f"пользователь {log.user_id} | вход: {log.input_data[:30]}"
                )
            text = "📋 *Последние 50 логов:*\n" + "\n".join(lines)
    await query.edit_message_text(text, parse_mode="Markdown")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with AsyncSessionLocal() as session:
        stmt = select(User).order_by(desc(User.joined_at)).limit(50)
        users = await session.execute(stmt)
        users = users.scalars().all()
        if not users:
            text = "Пользователей нет."
        else:
            lines = []
            for u in users:
                lines.append(
                    f"ID: {u.telegram_id} | {u.first_name} | баланс: {u.balance} | админ: {u.is_admin}"
                )
            text = "👥 *Последние пользователи:*\n" + "\n".join(lines)
    await query.edit_message_text(text, parse_mode="Markdown")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session:
        total_users = await session.execute(select(func.count()).select_from(User))
        total_users = total_users.scalar()
        total_logs = await session.execute(select(func.count()).select_from(RequestLog))
        total_logs = total_logs.scalar()
        total_ip = await session.execute(select(func.count()).select_from(IpLog))
        total_ip = total_ip.scalar()
        text = (
            f"📊 *Статистика:*\n"
            f"👥 Пользователей: {total_users}\n"
            f"📋 Запросов: {total_logs}\n"
            f"📟 IP-логов: {total_ip}"
        )
    await query.edit_message_text(text, parse_mode="Markdown")

async def admin_iplogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with AsyncSessionLocal() as session:
        stmt = select(IpLog).order_by(desc(IpLog.timestamp)).limit(50)
        logs = await session.execute(stmt)
        logs = logs.scalars().all()
        if not logs:
            text = "IP-логов нет."
        else:
            lines = []
            for log in logs:
                lines.append(
                    f"🕒 {log.timestamp.strftime('%Y-%m-%d %H:%M')} | пользователь {log.user_id} | IP: {log.ip}"
                )
            text = "📟 *Последние 50 IP-логов:*\n" + "\n".join(lines)
    await query.edit_message_text(text, parse_mode="Markdown")
