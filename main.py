import os
import asyncio
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import config
from bot_handlers import dp, bot
import db

async def start_clone_bot(token, owner_id):
    from bot_handlers import dp as clone_dp
    clone_bot = Bot(token=token)
    await clone_bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Справка")
    ])
    await clone_dp.start_polling(clone_bot, skip_updates=True)

async def start_all_clones():
    clones = db.get_all_active_clones()
    for clone_id, token, owner_id in clones:
        asyncio.create_task(start_clone_bot(token, owner_id))

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="admin", description="Админ-панель")
    ])

async def bot_polling():
    await set_commands()
    await bot.delete_webhook(drop_pending_updates=True)
    await start_all_clones()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    db.init_db()
    port = int(os.environ.get("PORT", 8000))  # <-- ГЛАВНОЕ ИСПРАВЛЕНИЕ
    # Запускаем веб-сервер (если он нужен для Render)
    # Если веб-сервер не нужен — запускаем только бота
    # Для Render нужен процесс, который слушает порт
    uvicorn.run("web_app:app", host="0.0.0.0", port=port)
