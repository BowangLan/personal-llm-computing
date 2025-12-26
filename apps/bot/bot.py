import logging
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters

from config import BOT_TOKEN
from observability import configure_logging, log_event, get_logger
from persistence import init_db
from handlers import (
    handle_message,
    handle_start,
    handle_help,
    handle_background,
    handle_status,
    handle_newsession,
    handle_sessions,
    handle_switch,
    handle_rename,
    handle_delsession,
    handle_session_callback,
    error_handler,
    post_init,
)


async def post_shutdown(app: Application):
    _logger = get_logger("bot.main")
    log_event(_logger, "bot_shutdown_complete")

def main():
    configure_logging()
    _logger = get_logger("bot.main")

    # Initialize database
    init_db()

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)  # Enable parallel processing
        .build()
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("newsession", handle_newsession))
    app.add_handler(CommandHandler("sessions", handle_sessions))
    app.add_handler(CommandHandler("switch", handle_switch))
    app.add_handler(CommandHandler("rename", handle_rename))
    app.add_handler(CommandHandler("delsession", handle_delsession))
    app.add_handler(CommandHandler("bg", handle_background))
    app.add_handler(CommandHandler("status", handle_status))

    # Add callback query handler for inline keyboard interactions
    app.add_handler(CallbackQueryHandler(handle_session_callback))

    app.add_error_handler(error_handler)

    log_event(_logger, "bot_starting")
    app.run_polling(drop_pending_updates=True, close_loop=True)

if __name__ == "__main__":
    main()
