import logging

import httpx
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
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Убираем шум от httpx и langchain при индексации
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain_community").setLevel(logging.WARNING)


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
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
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_error_handler(error_handler)

    # Снимаем webhook — иначе апдейты из групп уходят в старый URL, а не в polling
    r = httpx.get(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/deleteWebhook",
        params={"drop_pending_updates": True},
    )
    logger.info("deleteWebhook: %s", r.json())
    logger.info("Bot started!")
    app.run_polling(allowed_updates=["message", "channel_post", "callback_query"])


if __name__ == "__main__":
    main()
