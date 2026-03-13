import asyncio
import queue
import time
from datetime import datetime, timezone

import config
import rag
from bot.session_logger import save_session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для работы с кодовой базой KPD.\n\n"
        "Доступные команды:\n"
        "/list - Список доступных репозиториев\n"
        "/add <repo> - Добавить и проиндексировать репозиторий\n"
        "/remove <repo> - Удалить репозиторий\n"
        "/reindex <repo> - Переиндексировать репозиторий\n"
        "/status - Статус всех коллекций\n\n"
        "Просто напиши вопрос - и я отвечу на основе кода!"
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repos = config.REPOS_WHITELIST
    text = "📁 Доступные репозитории:\n\n"
    for repo in repos:
        exists = rag.collection_exists(repo)
        status = "✅" if exists else "❌"
        text += f"{status} {repo}\n"
    await update.message.reply_text(text)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _get_command_args(update, context)
    if not args:
        await update.message.reply_text("Usage: /add <repo_name>")
        return

    repo_name = args[0]
    
    if repo_name not in config.REPOS_WHITELIST:
        await update.message.reply_text(f"Репозиторий {repo_name} не в белом списке.")
        return
    
    await update.message.reply_text(f"🔄 Индексирую {repo_name}...")
    
    try:
        result = rag.index_repo(repo_name)
        if "error" in result:
            await update.message.reply_text(f"❌ Ошибка: {result['error']}")
        else:
            await update.message.reply_text(
                f"✅ Готово!\n"
                f"Репо: {result['repo']}\n"
                f"Чанков: {result['chunks']}\n"
                f"Векторов: {result['vectors']}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _get_command_args(update, context)
    if not args:
        await update.message.reply_text("Usage: /remove <repo_name>")
        return

    repo_name = args[0]
    
    if not rag.collection_exists(repo_name):
        await update.message.reply_text(f"Коллекция {repo_name} не существует.")
        return
    
    try:
        rag.delete_collection(repo_name)
        await update.message.reply_text(f"✅ Репозиторий {repo_name} удалён.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


def _get_command_args(update: Update, context: ContextTypes.DEFAULT_TYPE) -> list:
    """Аргументы команды: context.args или парсинг из текста (fallback для @bot в группах)."""
    if context.args:
        return context.args
    text = (update.message and update.message.text) or ""
    parts = text.split()
    return parts[1:] if len(parts) > 1 else []


async def reindex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = _get_command_args(update, context)
    if not args:
        keyboard = [
            [InlineKeyboardButton(repo, callback_data=f"reindex:{repo}")]
            for repo in config.REPOS_WHITELIST
        ]
        await update.message.reply_text(
            "Выбери репозиторий для переиндексации:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    repo_name = args[0]
    
    if repo_name not in config.REPOS_WHITELIST:
        await update.message.reply_text(f"Репозиторий {repo_name} не в белом списке.")
        return
    
    await update.message.reply_text(f"🔄 Переиндексирую {repo_name}...")
    
    try:
        if rag.collection_exists(repo_name):
            rag.delete_collection(repo_name)
        
        result = rag.index_repo(repo_name)
        if "error" in result:
            await update.message.reply_text(f"❌ Ошибка: {result['error']}")
        else:
            await update.message.reply_text(
                f"✅ Готово!\n"
                f"Чанков: {result['chunks']}\n"
                f"Векторов: {result['vectors']}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def reindex_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    repo_name = query.data.split(":", 1)[1]

    if repo_name not in config.REPOS_WHITELIST:
        await query.edit_message_text(f"Репозиторий {repo_name} не в белом списке.")
        return

    await query.edit_message_text(f"🔄 Переиндексирую {repo_name}...")

    try:
        if rag.collection_exists(repo_name):
            rag.delete_collection(repo_name)
        result = rag.index_repo(repo_name)
        if "error" in result:
            await query.edit_message_text(f"❌ Ошибка: {result['error']}")
        else:
            await query.edit_message_text(
                f"✅ Готово!\n"
                f"Чанков: {result['chunks']}\n"
                f"Векторов: {result['vectors']}"
            )
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Статус коллекций:\n\n"
    
    for repo in config.REPOS_WHITELIST:
        if rag.collection_exists(repo):
            info = rag.get_collection_info(repo)
            text += f"✅ {repo}: {info['vectors_count']} векторов\n"
        else:
            text += f"❌ {repo}: не создана\n"
    
    await update.message.reply_text(text)


# Макс. сообщений в контексте диалога для RAG (user + assistant пары)
_CHAT_HISTORY_LIMIT = 20


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text

    if question.startswith("/"):
        return

    status_queue = queue.Queue()

    def on_qdrant_status(text: str):
        status_queue.put(text)

    status_msg = await update.message.reply_text("🤔 Думаю...")

    history = list(context.chat_data.get("history", []))[-_CHAT_HISTORY_LIMIT:]
    user = update.effective_user
    t0 = time.monotonic()
    answer = None
    session_data = {}
    loop = asyncio.get_event_loop()

    try:
        future = loop.run_in_executor(
            None,
            lambda: rag.generate_answer(question, history=history, on_status=on_qdrant_status),
        )
        while not future.done():
            try:
                line = status_queue.get_nowait()
                await status_msg.edit_text(line)
            except queue.Empty:
                pass
            await asyncio.sleep(0.15)
        answer, session_data = future.result()
        await status_msg.edit_text("✅ Готово.")
        await update.message.reply_text(answer)
        # Дополняем историю для следующих вопросов
        h = context.chat_data.setdefault("history", [])
        h.append({"role": "user", "content": question})
        h.append({"role": "assistant", "content": answer})
        context.chat_data["history"] = h[-_CHAT_HISTORY_LIMIT:]
    except Exception as e:
        answer = f"❌ Ошибка: {str(e)}"
        await update.message.reply_text(answer)
    finally:
        save_session({
            "ts": datetime.now(timezone.utc).isoformat(),
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "question": question,
            "answer": answer,
            "duration_s": round(time.monotonic() - t0, 2),
            **session_data,
        })


def is_allowed(user_id: int) -> bool:
    if not config.TELEGRAM_WHITELIST_USERS:
        return True
    return str(user_id) in config.TELEGRAM_WHITELIST_USERS


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update and update.message:
        await update.message.reply_text(f"Произошла ошибка: {context.error}")
