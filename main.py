"""Combined launcher: Telegram bot + Web UI."""
import asyncio
import logging
import threading
import sys

import httpx
import uvicorn
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import config
from bot import (
    start_command,
    list_command,
    add_command,
    remove_command,
    reindex_command,
    reindex_callback,
    status_command,
    mode_command,
    mode_callback,
    handle_message,
    error_handler,
    adduser_command,
    removeuser_command,
    listusers_command,
    id_command,
)
from web.main import app as fastapi_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain_community").setLevel(logging.WARNING)


def run_telegram():
    """Run Telegram bot in a separate thread."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping Telegram bot")
        return
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("remove", remove_command))
    app.add_handler(CommandHandler("reindex", reindex_command))
    app.add_handler(CallbackQueryHandler(reindex_callback, pattern=r"^reindex:"))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CallbackQueryHandler(mode_callback, pattern=r"^mode:"))
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(CommandHandler("listusers", listusers_command))
    app.add_handler(CommandHandler("id", id_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    # Delete webhook for polling
    try:
        r = httpx.get(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/deleteWebhook",
            params={"drop_pending_updates": True},
        )
        logger.info("deleteWebhook: %s", r.json())
    except Exception as e:
        logger.warning(f"Failed to delete webhook: {e}")
    
    logger.info("Telegram bot starting...")
    app.run_polling(allowed_updates=["message", "channel_post", "callback_query"])


def run_web():
    """Run FastAPI web server."""
    logger.info("Starting Web UI on http://0.0.0.0:8000")
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


def main():
    """Run both Telegram bot and Web UI."""
    logger.info("=" * 50)
    logger.info("ASTRA-M — Starting all services")
    logger.info("=" * 50)
    
    # Start Telegram in a separate thread
    telegram_thread = threading.Thread(target=run_telegram, daemon=True)
    telegram_thread.start()
    
    # Run Web UI in main thread
    try:
        run_web()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
