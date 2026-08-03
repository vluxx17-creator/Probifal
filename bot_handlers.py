from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import config, db, api_handlers
import datetime
import json
import os
import random
import string
import html

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    waiting_broadcast = State()
    waiting_promote_user = State()
    waiting_reset_user = State()
    waiting_clone_token = State()

# ---------- МЕНЮ (кнопки в 2 строки) ----------
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Пробив", callback_data="menu_search"),
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="menu_profile")
        ],
        [
            InlineKeyboardButton(text="🤖 Создать бота-копию", callback_data="menu_create_clone"),
            InlineKeyboardButton(text="📋 Мои боты", callback_data="menu_my_clones")
        ],
        [
            InlineKeyboardButton(text="⭐ Купить запросы", callback_data="menu_buy_requests")
        ]
    ])
    return kb

def search_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 VK по имени", callback_data="search_vk"),
            InlineKeyboardButton(text="🌐 IP-адрес", callback_data="search_ip")
        ],
        [
            InlineKeyboardButton(text="🏠 Домен (whois)", callback_data="search_domain"),
            InlineKeyboardButton(text="🔎 Никнейм", callback_data="search_nick")
        ],
        [
            InlineKeyboardButton(text="📱 Номер телефона", callback_data="search_phone")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")
        ]
    ])
    return kb

def admin_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="📜 Все логи", callback_data="admin_logs_all"),
            InlineKeyboardButton(text="➕ Выдать запросы", callback_data="admin_give")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить баланс", callback_data="admin_reset"),
            InlineKeyboardButton(text="👑 Назначить админа", callback_data="admin_promote")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")
        ]
    ])
    return kb

def tariff_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="20 запр. — 75 ⭐", callback_data="buy_20"),
            InlineKeyboardButton(text="30 запр. — 150 ⭐", callback_data="buy_30")
        ],
        [
            InlineKeyboardButton(text="50 запр. — 200 ⭐", callback_data="buy_50"),
            InlineKeyboardButton(text="100 запр. — 300 ⭐", callback_data="buy_100")
        ],
        [
            InlineKeyboardButton(text="500 запр. — 600 ⭐", callback_data="buy_500"),
            InlineKeyboardButton(text="1000 запр. — 1200 ⭐", callback_data="buy_1000")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")
        ]
    ])
    return kb

# ---------- КОМАНДЫ ----------
@dp.message(Command("start"))
async def start_cmd(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    if user.id == config.ADMIN_ID:
        db.set_admin(user.id, 1)
    
    balance = db.get_balance(user.id)
    is_admin = db.is_admin(user.id)
    admin_text = "🔹 Вы администратор\n" if is_admin else ""
    
    text = (
        "<b>🕵️ Phantom — профессиональный инструмент для поиска информации</b>\n\n"
        "Я умею находить данные по открытым источникам:\n"
        "• <b>VK</b> — поиск людей по имени с фото, городом, датой рождения\n"
        "• <b>IP-адрес</b> — геолокация, провайдер, координаты\n"
        "• <b>Домен</b> — whois-информация, регистратор, даты\n"
        "• <b>Никнейм</b> — проверка на GitHub, Telegram, Twitter, Instagram, VK\n"
        "• <b>Номер телефона</b> — оператор, страна, регион + поиск в соцсетях\n\n"
        f"💰 <b>Ваш баланс:</b> {balance} запросов\n"
        f"{admin_text}\n"
        "Выберите действие:"
    )
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "<b>📖 Справка Phantom</b>\n\n"
        "Все функции доступны через кнопки.\n"
        "Администратор: /admin\n"
        "Купить запросы: кнопка «Купить запросы» в главном меню.",
        parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id == config.ADMIN_ID:
        db.set_admin(message.from_user.id, 1)
    if not db.is_admin(message.from_user.id):
        await message.answer("⛔ Нет прав.")
        return
    await message.answer("⚙️ Админ-панель", reply_markup=admin_menu())

# ---------- ОБРАБОТЧИКИ СОСТОЯНИЙ ----------
@dp.message(AdminStates.waiting_clone_token)
async def handle_clone_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if not token.startswith("7") or len(token) < 40:
        await message.answer("❌ Невалидный токен. Скопируйте токен от @BotFather.", parse_mode="HTML")
        return
    try:
        test_bot = Bot(token=token)
        me = await test_bot.get_me()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {html.escape(str(e))}", parse_mode="HTML")
        return
    db.add_clone(token, message.from_user.id)
    await message.answer(f"✅ Бот @{html.escape(me.username)} добавлен как копия Phantom.", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_user_id)
async def admin_give_requests(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) == 2 and parts[1].isdigit():
        user_id = int(parts[0])
        amount = int(parts[1])
        db.add_requests(user_id, amount)
        await message.answer(f"✅ Пользователю {user_id} выдано {amount} запросов.", parse_mode="HTML")
    else:
        await message.answer("Неверный формат. Используйте: ID количество", parse_mode="HTML")
    await state.clear()

@dp.message(AdminStates.waiting_amount)
async def admin_reset_balance(message: Message, state: FSMContext):
    user_id = int(message.text.strip()) if message.text.strip().isdigit() else None
    if user_id:
        # Устанавливаем баланс в 0
        conn = sqlite3.connect(db.DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET requests_balance=0 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Баланс пользователя {user_id} обнулён.", parse_mode="HTML")
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

# ---------- ОБРАБОТЧИКИ МЕНЮ ----------
@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = callback.data
    if data == "menu_main":
        balance = db.get_balance(callback.from_user.id)
        await callback.message.edit_text(
            f"<b>🕵️ Phantom</b>\n\n💰 Баланс: {balance} запросов\n\nВыберите действие:",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    elif data == "menu_search":
        await callback.message.edit_text(
            "<b>🔍 Выберите тип пробива:</b>",
            reply_markup=search_menu(),
            parse_mode="HTML"
        )
    elif data == "menu_create_clone":
        await callback.message.answer("Отправьте токен бота от @BotFather.", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_clone_token)
    elif data == "menu_my_clones":
        clones = db.get_clones_by_owner(callback.from_user.id)
        if not clones:
            await callback.message.edit_text("У вас нет ботов-копий.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
            ]), parse_mode="HTML")
            return
        text = "<b>Ваши боты-копии:</b>\n\n"
        for clone in clones:
            clone_id, token, created_at, is_active = clone
            status = "✅ активен" if is_active else "❌ отключён"
            created_str = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
            text += f"ID: {clone_id} | {status} | создан: {created_str}\n"
        await callback.message.edit_text(text[:4000], reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
        ]), parse_mode="HTML")
    elif data == "menu_profile":
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        if user:
            balance = db.get_balance(user_id)
            is_admin = "Да" if user[4] == 1 else "Нет"
            text = f"<b>👤 Ваш профиль</b>\n\nID: <code>{user[0]}</code>\nИмя: {html.escape(user[2])} {html.escape(user[3])}\nБаланс запросов: {balance}\nАдминистратор: {is_admin}"
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
            ]), parse_mode="HTML")
        else:
            await callback.message.edit_text("Профиль не найден.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
            ]), parse_mode="HTML")
    elif data == "menu_buy_requests":
        await callback.message.edit_text(
            "<b>⭐ Выберите тариф</b>\n\nЧем больше пакет — тем дешевле каждый запрос. Экономия до 70%.",
            reply_markup=tariff_menu(),
            parse_mode="HTML"
        )

# ---------- ПОКУПКА ТАРИФОВ ----------
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_tariff(callback: CallbackQuery):
    await callback.answer()
    amount = int(callback.data.replace("buy_", ""))
    price = config.TARIFFS.get(amount)
    if not price:
        await callback.message.answer("❌ Тариф не найден.")
        return
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Пакет {amount} запросов",
        description=f"Пополнение баланса на {amount} запросов для Phantom",
        payload=f"requests_{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{amount} запросов", amount=price)],
        start_parameter="buy_requests"
    )
    await callback.message.answer("💳 Для оплаты нажмите кнопку ниже.")

@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("requests_"):
        amount = int(payload.replace("requests_", ""))
        db.add_requests(message.from_user.id, amount)
        balance = db.get_balance(message.from_user.id)
        await message.answer(
            f"⭐ <b>Оплата успешна!</b>\n\n"
            f"На ваш баланс добавлено {amount} запросов.\n"
            f"Текущий баланс: {balance} запросов.",
            parse_mode="HTML"
        )
    else:
        await message.answer("Оплата прошла, но пакет не распознан. Обратитесь к администратору.", parse_mode="HTML")

# ---------- ПОИСК ----------
@dp.callback_query(lambda c: c.data.startswith("search_"))
async def search_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    can, msg = db.can_make_request(callback.from_user.id)
    if not can:
        await callback.message.answer(f"⛔ {html.escape(msg)}", parse_mode="HTML")
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
    current_state = await state.get_state()
    if current_state is not None:
        return
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
        await message.answer(f"⛔ {html.escape(msg)}", parse_mode="HTML")
        await state.clear()
        return
    # Списываем запрос
    db.use_request(message.from_user.id)
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
        output = f"<b>❌ Ошибка:</b> <code>{html.escape(data['error'])}</code>"
    else:
        if search_type == "phone":
            output = "<b>📱 Результаты по номеру телефона:</b>\n\n"
            for key, value in data.items():
                if isinstance(value, dict):
                    output += f"<b>{key}:</b>\n"
                    for k, v in value.items():
                        output += f"  {k}: {html.escape(str(v))}\n"
                else:
                    output += f"<b>{key}</b>: {html.escape(str(value))}\n"
        else:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            output = f"<b>Результаты ({html.escape(search_type)}):</b>\n<pre>{html.escape(json_str[:3000])}</pre>"
    output += "\n\n<blockquote>Данные из открытых источников.</blockquote>"
    await message.answer(output, parse_mode="HTML")
    db.add_log(message.from_user.id, f"search_{search_type}", query, output[:500])

# ---------- АДМИН-КОЛБЭКИ ----------
@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id == config.ADMIN_ID:
        db.set_admin(callback.from_user.id, 1)
    if not db.is_admin(callback.from_user.id):
        await callback.message.answer("⛔ Нет прав.", parse_mode="HTML")
        return
    data = callback.data
    if data == "admin_list":
        users = db.get_all_users()
        text = "<b>Список пользователей:</b>\n"
        for u in users:
            admin = "✅" if u[4] else "❌"
            balance = db.get_balance(u[0])
            username = html.escape(u[1]) if u[1] else "—"
            text += f"<code>{u[0]}</code> @{username} | баланс: {balance} | админ {admin}\n"
        await callback.message.answer(text[:4000], parse_mode="HTML")
    elif data == "admin_broadcast":
        await callback.message.answer("Введите текст для рассылки:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_broadcast)
    elif data == "admin_logs_all":
        logs = db.get_all_logs(limit=50)
        if not logs:
            await callback.message.answer("Логов нет.")
        else:
            text = "<b>Последние логи:</b>\n\n"
            for log in logs:
                text += f"<code>{log[1]}</code> | {html.escape(log[2])} | {html.escape(log[3])} | {html.escape(log[4][:50])}\n"
            await callback.message.answer(text[:4000], parse_mode="HTML")
    elif data == "admin_give":
        await callback.message.answer("Введите ID пользователя и количество запросов через пробел:\n<code>123456 50</code>", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_user_id)
    elif data == "admin_reset":
        await callback.message.answer("Введите ID пользователя для обнуления баланса:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_amount)
    elif data == "admin_promote":
        await callback.message.answer("Введите ID пользователя для назначения админом:", parse_mode="HTML")
        await state.set_state(AdminStates.waiting_promote_user)
