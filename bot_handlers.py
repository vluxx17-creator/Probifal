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

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

# ---------- ГЛАВНОЕ МЕНЮ ----------
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Пробив", callback_data="menu_search")],
        [InlineKeyboardButton(text="🪞 Создать зеркало", callback_data="menu_create_mirror")],
        [InlineKeyboardButton(text="📡 Логер", callback_data="menu_logger")],
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
        [InlineKeyboardButton(text="➕ Выдать подписку", callback_data="admin_give")],
        [InlineKeyboardButton(text="➖ Отозвать подписку", callback_data="admin_revoke")],
        [InlineKeyboardButton(text="📜 Логи пользователя", callback_data="admin_logs")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])
    return kb

# ---------- КОМАНДА /start ----------
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    if user.id == config.ADMIN_ID:
        db.set_admin(user.id, 1)
    # Проверяем, есть ли у пользователя остаток запросов
    can, _ = db.can_make_request(user.id)
    if not can:
        remaining = 0
    else:
        daily, _ = db.get_daily_requests(user.id)
        remaining = 2 - daily if not db.is_subscribed(user.id) else "∞"
    status_text = f"Осталось запросов сегодня: {remaining}" if isinstance(remaining, int) else "Безлимит (подписка)"
    
    await message.answer(
        f"<b>🕵️ Phantom — универсальный инструмент для поиска и сбора данных</b>\n\n"
        f"<i>{status_text}</i>\n\n"
        "Выберите действие в меню ниже:\n"
        "• <b>Пробив</b> – поиск по VK, IP, домену, нику или телефону\n"
        "• <b>Зеркало</b> – создайте ссылку для сбора данных о посетителях\n"
        "• <b>Логер</b> – просмотр ваших зеркал и статистики\n"
        "• <b>Профиль</b> – информация о подписке\n"
        "• <b>Купить подписку</b> – оформите доступ к расширенным функциям",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "<b>📖 Справка Phantom</b>\n\n"
        "Все функции доступны через кнопки в главном меню.\n"
        "Если вы администратор, используйте команду /admin для панели управления.",
        parse_mode="HTML"
    )

# ---------- ОБРАБОТЧИКИ МЕНЮ ----------
@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = callback.data

    if data == "menu_main":
        await callback.message.edit_text(
            "<b>🕵️ Phantom — главное меню</b>",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    elif data == "menu_search":
        await callback.message.edit_text(
            "<b>🔍 Выберите тип пробива:</b>",
            reply_markup=search_menu(),
            parse_mode="HTML"
        )
    elif data == "menu_create_mirror":
        await create_mirror_for_user(callback.message)
        await callback.message.edit_text(
            "Зеркало создано! Вернитесь в главное меню.",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    elif data == "menu_logger":
        mirrors = db.get_mirrors_by_user(callback.from_user.id)
        if mirrors:
            text = "<b>📡 Ваши зеркала:</b>\n\n"
            for path, visits, created_at in mirrors:
                created_str = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
                host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost")
                link = f"https://{host}/mirror/{path}"
                text += f"🔗 <a href='{link}'>{link}</a>\n"
                text += f"   👁️ посещений: {visits}, создано: {created_str}\n\n"
            await callback.message.edit_text(text[:4000], reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
            ]), parse_mode="HTML", disable_web_page_preview=True)
        else:
            await callback.message.edit_text(
                "У вас пока нет зеркал. Создайте новое через кнопку «Создать зеркало».",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
                ]),
                parse_mode="HTML"
            )
    elif data == "menu_profile":
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        if user:
            sub_until = user[4]
            if sub_until and sub_until > int(datetime.datetime.now().timestamp()):
                days_left = (sub_until - int(datetime.datetime.now().timestamp())) // 86400
                status = f"✅ Активна, осталось {days_left} дн."
            else:
                status = "❌ Неактивна"
            # Получаем остаток запросов
            can, _ = db.can_make_request(user_id)
            if can:
                daily, _ = db.get_daily_requests(user_id)
                remaining = 2 - daily if not db.is_subscribed(user_id) else "∞"
            else:
                remaining = 0
            text = f"<b>👤 Ваш профиль</b>\n\n"
            text += f"ID: <code>{user[0]}</code>\n"
            text += f"Имя: {user[2]} {user[3]}\n"
            text += f"Статус подписки: {status}\n"
            text += f"Остаток запросов сегодня: {remaining}\n"
            if user[5] == 1:
                text += "🔹 Вы администратор\n"
        else:
            text = "Профиль не найден."
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
        ]), parse_mode="HTML")
    elif data == "menu_buy_subscription":
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Подписка Phantom на 30 дней",
            description="Полный доступ ко всем функциям бота на 30 дней",
            payload="subscription_30days",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Подписка 30 дней", amount=100)],
            start_parameter="subscribe"
        )
        await callback.message.answer("💳 Для оплаты нажмите кнопку ниже.")
    elif data == "menu_admin":
        if not db.is_admin(callback.from_user.id):
            await callback.message.answer("⛔ <b>Нет прав.</b>", parse_mode="HTML")
            return
        await callback.message.edit_text(
            "<b>⚙️ Админ-панель</b>",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

# ---------- ОБРАБОТЧИКИ ПОИСКА ----------
@dp.callback_query(lambda c: c.data.startswith("search_"))
async def search_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    search_type = callback.data.replace("search_", "")
    # Проверяем лимит перед тем, как предложить ввести данные
    can, msg = db.can_make_request(callback.from_user.id)
    if not can:
        await callback.message.answer(f"⛔ {msg}", parse_mode="HTML")
        return
    await state.set_data({"search_type": search_type})
    prompts = {
        "vk": "Введите <b>имя</b> для поиска в ВК (например: <i>Иван Петров</i>):",
        "ip": "Введите <b>IP-адрес</b> (например: <code>8.8.8.8</code>):",
        "domain": "Введите <b>домен</b> (например: <code>example.com</code>):",
        "nick": "Введите <b>никнейм</b> (например: <i>john_doe</i>):",
        "phone": "Введите <b>номер телефона</b> в международном формате (например: <code>79001234567</code>):"
    }
    await callback.message.answer(prompts.get(search_type, "Введите данные:"), parse_mode="HTML")

# ---------- ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (ввод данных) ----------
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

    # Проверяем лимит ещё раз (пользователь мог ввести данные позже)
    can, msg = db.can_make_request(message.from_user.id)
    if not can:
        await message.answer(f"⛔ {msg}", parse_mode="HTML")
        await state.clear()
        return

    # Увеличиваем счётчик запросов
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
            output = "<b>📱 Результаты пробива по номеру телефона:</b>\n\n"
            for key, value in data.items():
                output += f"<b>{key}</b>: {value}\n"
        else:
            output = f"<b>✅ Результаты пробива ({search_type}):</b>\n<pre>{json.dumps(data, ensure_ascii=False, indent=2)[:3000]}</pre>"
    output += "\n\n<blockquote>Данные получены из открытых источников.</blockquote>"
    await message.answer(output, parse_mode="HTML")
    db.add_log(message.from_user.id, f"search_{search_type}", query, output[:500])

async def create_mirror_for_user(message):
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost")
    path = generate_mirror_path()
    db.create_mirror(path, message.from_user.id)
    full_link = f"https://{host}/mirror/{path}"
    db.add_log(message.from_user.id, "create_mirror", path, full_link)
    await message.answer(
        f"<b>🪞 Зеркало создано!</b>\n\n"
        f"Ваша уникальная ссылка:\n<code>{full_link}</code>\n\n"
        "Переходите по ней, чтобы собирать данные о посетителях.\n"
        "Все переходы будут зафиксированы в логах.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть зеркало", url=full_link)],
            [InlineKeyboardButton(text="📋 Мои зеркала", callback_data="menu_logger")]
        ]),
        parse_mode="HTML"
    )

def generate_mirror_path(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# ---------- ОПЛАТА ПОДПИСКИ ----------
@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    until = int(datetime.datetime.now().timestamp()) + 30*86400
    db.update_subscription(user_id, until)
    # После покупки сбрасываем счётчик запросов (чтобы сразу можно было пользоваться)
    conn = sqlite3.connect(db.DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET daily_requests=0, last_request_date=? WHERE user_id=?", (int(datetime.datetime.now().timestamp()), user_id))
    conn.commit()
    conn.close()
    await message.answer(
        "⭐ <b>Оплата прошла успешно!</b>\n\n"
        "Ваша подписка активирована на 30 дней.\n"
        "Теперь вам доступны все функции пробива без ограничений.",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            chat_id=config.STARS_RECEIVER,
            text=f"⭐ Получена оплата подписки от пользователя {user_id} (@{message.from_user.username})"
        )
    except Exception as e:
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
        await callback.message.answer("⛔ <b>Нет прав.</b>", parse_mode="HTML")
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
    elif data == "admin_give":
        await callback.message.answer("Введите <b>ID пользователя</b> и <b>количество дней</b> через пробел:\n<code>123456 30</code>", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_user_id)
    elif data == "admin_revoke":
        await callback.message.answer("Введите <b>ID пользователя</b> для отзыва подписки:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_days)
    elif data == "admin_logs":
        await callback.message.answer("Введите <b>ID пользователя</b> для просмотра логов:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_days)

@dp.message(AdminStates.waiting_user_id)
async def admin_give_access(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        user_id = int(parts[0])
        days = int(parts[1])
        until = int(datetime.datetime.now().timestamp()) + days*86400
        db.update_subscription(user_id, until)
        # Сбрасываем счётчик
        conn = sqlite3.connect(db.DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET daily_requests=0, last_request_date=? WHERE user_id=?", (int(datetime.datetime.now().timestamp()), user_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ <b>Пользователю {user_id} выдан доступ на {days} дней.</b>", parse_mode="HTML")
    else:
        await message.answer("Неверный формат. Используйте: <code>ID пробел количество_дней</code>", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_days)
async def admin_revoke_or_logs(message: Message, state: FSMContext):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if not user_id:
        await message.answer("Введите корректный <b>ID</b>", parse_mode="HTML")
        return
    await message.answer("Что сделать? Напишите <b>revoke</b> для отзыва или <b>logs</b> для просмотра логов.", parse_mode="HTML")
    await state.update_data(user_id=user_id)

@dp.message(lambda message: message.text.lower() in ["revoke", "logs"])
async def admin_action_confirm(message: Message, state: FSMContext):
    action = message.text.lower()
    data = await state.get_data()
    user_id = data.get("user_id")
    if not user_id:
        await message.answer("Сначала введите ID.")
        return
    if action == "revoke":
        db.update_subscription(user_id, 0)
        await message.answer(f"✅ <b>Подписка пользователя {user_id} отозвана.</b>", parse_mode="HTML")
    elif action == "logs":
        logs = db.get_user_logs(user_id)
        if not logs:
            await message.answer("Логов нет.")
        else:
            text = "<b>Логи пользователя</b>\n"
            for l in logs[:10]:
                text += f"<code>{l[1]}</code> – {l[2]} – {l[3][:100]}\n"
            await message.answer(text[:4000], parse_mode="HTML")
    await state.clear()
