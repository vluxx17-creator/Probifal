import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, PreCheckoutQueryHandler
from config import Config
from handlers.start import start
from handlers.buttons import button_callback
from handlers.input import handle_text
from handlers.payments import buy_callback, precheckout, successful_payment
from handlers.admin import admin_panel, admin_logs, admin_users, admin_stats, admin_iplogs, admin_grant, admin_add_balance
from database import init_db

logging.basicConfig(level=logging.INFO)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    logging.info("Health server running on port 8080")
    server.serve_forever()

async def post_init(application):
    await init_db()
    logging.info("База данных инициализирована (SQLite)")

def main():
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    app = ApplicationBuilder().token(Config.BOT_TOKEN).post_init(post_init).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    
    # Callback-запросы (кнопки)
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(phone|ip|address|vk|balance|buy|help|admin|myip)$"))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin$"))
    app.add_handler(CallbackQueryHandler(admin_logs, pattern="^admin_logs$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_iplogs, pattern="^admin_iplogs$"))
    app.add_handler(CallbackQueryHandler(admin_grant, pattern="^admin_grant$"))
    app.add_handler(CallbackQueryHandler(admin_add_balance, pattern="^admin_add_balance$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("Главное меню /start"), pattern="^back_to_menu$"))
    
    # Текстовые сообщения (ввод данных) – ЕДИНСТВЕННЫЙ обработчик
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Платежи
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    logging.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
