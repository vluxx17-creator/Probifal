from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.phone import phone_lookup
from services.ip import ip_lookup, domain_lookup
from services.address import address_lookup
from services.vk import vk_lookup
from utils.balance import get_user_balance, deduct_balance, add_balance
from utils.free_requests import get_free_requests, use_free_request
from database import AsyncSessionLocal
from models import RequestLog, IpLog
import json
from datetime import datetime
import aiohttp

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    telegram_id = user_id

    if data == "phone":
        free = await get_free_requests(telegram_id, "phone")
        if free > 0:
            await use_free_request(telegram_id, "phone")
            context.user_data["free_used"] = True
        else:
            if not await deduct_balance(telegram_id):
                await query.edit_message_text("❌ У вас закончились запросы. Купите пакет в разделе 💰.")
                return
        await query.edit_message_text("📞 Введите номер телефона (например, +79001234567):")
        context.user_data["awaiting"] = "phone_input"
    
    elif data == "ip":
        free = await get_free_requests(telegram_id, "ip")
        if free > 0:
            await use_free_request(telegram_id, "ip")
            context.user_data["free_used"] = True
        else:
            if not await deduct_balance(telegram_id):
                await query.edit_message_text("❌ Недостаточно запросов.")
                return
        await query.edit_message_text("🌐 Введите IP-адрес или домен:")
        context.user_data["awaiting"] = "ip_input"
    
    elif data == "address":
        free = await get_free_requests(telegram_id, "address")
        if free > 0:
            await use_free_request(telegram_id, "address")
            context.user_data["free_used"] = True
        else:
            if not await deduct_balance(telegram_id):
                await query.edit_message_text("❌ Недостаточно запросов.")
                return
        await query.edit_message_text("📍 Введите адрес (страна, город, улица, дом):")
        context.user_data["awaiting"] = "address_input"
    
    elif data == "vk":
        free = await get_free_requests(telegram_id, "vk")
        if free > 0:
            await use_free_request(telegram_id, "vk")
            context.user_data["free_used"] = True
        else:
            if not await deduct_balance(telegram_id):
                await query.edit_message_text("❌ Недостаточно запросов.")
                return
        await query.edit_message_text("🎯 Введите ссылку на профиль VK или ID:")
        context.user_data["awaiting"] = "vk_input"
    
    elif data == "balance":
        balance = await get_user_balance(telegram_id)
        free_phone = await get_free_requests(telegram_id, "phone")
        free_ip = await get_free_requests(telegram_id, "ip")
        free_addr = await get_free_requests(telegram_id, "address")
        free_vk = await get_free_requests(telegram_id, "vk")
        msg = (
            f"📊 *Ваш баланс:*\n"
            f"🟢 Платных запросов: {balance}\n"
            f"🔹 Бесплатных (номер): {free_phone}\n"
            f"🔹 Бесплатных (IP/домен): {free_ip}\n"
            f"🔹 Бесплатных (адрес): {free_addr}\n"
            f"🔹 Бесплатных (VK): {free_vk}\n\n"
            "💰 Пополнить баланс можно через раздел 'Купить звёзды'."
        )
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    elif data == "buy":
        from handlers.payments import build_packages_keyboard
        keyboard = build_packages_keyboard()
        await query.edit_message_text(
            "💎 *Выберите пакет запросов:*\n"
            "Цены указаны в звёздах Telegram.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    elif data == "help":
        help_text = (
            "🆘 *Помощь по ProbifAm*\n\n"
            "🔍 *Пробив по номеру* — данные оператора, геолокация, регион.\n"
            "🌐 *Пробив по IP/домену* — геолокация, провайдер, WHOIS (для домена).\n"
            "📍 *Пробив по адресу* — координаты, почтовый индекс, тип объекта.\n"
            "🎯 *Пробив по VK* — базовая информация профиля (если открыт).\n"
            "💰 *Купить звёзды* — пополнить баланс платных запросов.\n"
            "📊 *Мои запросы* — остаток платных и бесплатных.\n"
            "📟 *Мой IP* — узнать свой публичный IP и сохранить в лог.\n"
            "⚙️ *Админ-панель* (только для администратора).\n\n"
            "Бесплатно: 2 попытки по каждому типу."
        )
        await query.edit_message_text(help_text, parse_mode="Markdown")
    
    elif data == "myip":
        # Получаем IP через ipify и сохраняем в лог
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org?format=json") as resp:
                ip_data = await resp.json()
                ip = ip_data.get("ip")
                if ip:
                    async with AsyncSessionLocal() as db:
                        log = IpLog(user_id=telegram_id, ip=ip)
                        db.add(log)
                        await db.commit()
                    await query.edit_message_text(f"📟 Ваш публичный IP: `{ip}`\n(записан в лог)", parse_mode="Markdown")
                else:
                    await query.edit_message_text("❌ Не удалось определить IP.")
    
    elif data == "admin":
        from handlers.admin import admin_panel
        await admin_panel(update, context)
    
    else:
        await query.edit_message_text("Неизвестная команда. Используйте /start.")
