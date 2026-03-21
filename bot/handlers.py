import asyncio
import logging
import queue
import re
import time
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)
import rag
from rag.validation import validate_user_question
from web.state import state
from bot.session_logger import save_session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.error import BadRequest
# html_escape defined below

async def _safe_edit_text(msg, text: str) -> bool:
    """Редактирует сообщение; игнорирует Telegram 'Message is not modified'."""
    try:
        await msg.edit_text(text)
        return True
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return False  # Тот же текст — ничего не делаем
        raise
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id if user else None):
        return
    await update.message.reply_text(
        "👋 Привет! Я бот для вопросов по коду в подключённых репозиториях.\n\n"
        "Доступные команды:\n"
        "/list - Список доступных репозиториев\n"
        "/add <repo> - Добавить и проиндексировать репозиторий\n"
        "/remove <repo> - Удалить репозиторий\n"
        "/reindex <repo> - Переиндексировать репозиторий\n"
        "/status - Статус всех коллекций\n\n"
        "Просто напиши вопрос — и я отвечу на основе кода!\n\n"
        "В группе: напиши @бот вопрос — бот ответит только при упоминании."
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id if user else None):
        return
    repos = rag.list_collections()
    text = "📁 Проиндексированные репозитории:\n\n"
    if not repos:
        text += "Нет проиндексированных репозиториев."
    else:
        for repo in repos:
            info = rag.get_collection_info(repo)
            text += f"✅ {repo}: {info['vectors_count']} векторов\n"
    await update.message.reply_text(text)


async def _run_index_async(repo_name: str, resume: bool, progress_queue: queue.Queue) -> dict:
    progress_values = {"idx": 0, "total": 0, "path": "", "chunks": 0, "vectors": 0, "skipped": False}

    def on_progress(idx: int, total: int, path: str, chunks: int, vectors: int, skipped: bool):
        progress_values.update({"idx": idx, "total": total, "path": path, "chunks": chunks, "vectors": vectors, "skipped": skipped})
        progress_queue.put(dict(progress_values))

    return await rag.index_repo_async(repo_name, resume=resume, on_progress=on_progress)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id if user else None):
        return
    args = _get_command_args(update, context)
    if not args:
        await update.message.reply_text("Usage: /add <repo_name>")
        return

    repo_name = args[0]
    
    progress_queue = queue.Queue()
    status_msg = await update.message.reply_text(f"🔄 Индексирую {repo_name}...")

    try:
        index_task = asyncio.create_task(_run_index_async(repo_name, resume=True, progress_queue=progress_queue))
        while not index_task.done():
            try:
                p = progress_queue.get_nowait()
                text = _format_index_progress(repo_name, p)
                await _safe_edit_text(status_msg, text)
            except queue.Empty:
                pass
            await asyncio.sleep(0.2)
        result = index_task.result()
        if "error" in result:
            await _safe_edit_text(status_msg, f"❌ Ошибка: {result['error']}")
        else:
            await _safe_edit_text(status_msg,
                f"✅ Готово!\n"
                f"Репо: {result['repo']}\n"
                f"Чанков: {result['chunks']}\n"
                f"Векторов: {result['vectors']}"
            )
    except Exception as e:
        await _safe_edit_text(status_msg, f"❌ Ошибка: {str(e)}")


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id if user else None):
        return
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


def _format_index_progress(repo_name: str, p: dict) -> str:
    idx, total, path, chunks, vectors = p["idx"], p["total"], p["path"], p["chunks"], p["vectors"]
    short_path = path if len(path) <= 45 else "..." + path[-42:]
    mark = "⏭" if p.get("skipped") else "✓"
    return f"🔄 {repo_name}\n{idx}/{total} файлов · {chunks} чанков · {vectors} векторов\n{mark} {short_path}"


def _get_command_args(update: Update, context: ContextTypes.DEFAULT_TYPE) -> list:
    """Аргументы команды: context.args или парсинг из текста (fallback для @bot в группах)."""
    if context.args:
        return context.args
    text = (update.message and update.message.text) or ""
    parts = text.split()
    return parts[1:] if len(parts) > 1 else []


async def reindex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id if user else None):
        return
    args = _get_command_args(update, context)
    if not args:
        keyboard = [
            [InlineKeyboardButton(repo, callback_data=f"reindex:{repo}")]
            for repo in rag.list_collections()
        ]
        await update.message.reply_text(
            "Выбери репозиторий для переиндексации:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    repo_name = args[0]
    
    status_msg = await update.message.reply_text(f"🔄 Переиндексирую {repo_name}...")
    await _run_reindex(status_msg, repo_name)


async def _run_reindex(status_msg, repo_name: str):
    progress_queue = queue.Queue()

    try:
        if rag.collection_exists(repo_name):
            rag.delete_collection(repo_name)

        index_task = asyncio.create_task(_run_index_async(repo_name, resume=False, progress_queue=progress_queue))
        while not index_task.done():
            try:
                p = progress_queue.get_nowait()
                await _safe_edit_text(status_msg, _format_index_progress(repo_name, p))
            except queue.Empty:
                pass
            await asyncio.sleep(0.2)
        result = index_task.result()
        if "error" in result:
            await _safe_edit_text(status_msg, f"❌ Ошибка: {result['error']}")
        else:
            await _safe_edit_text(status_msg,
                f"✅ Готово!\n"
                f"Чанков: {result['chunks']}\n"
                f"Векторов: {result['vectors']}"
            )
    except Exception as e:
        await _safe_edit_text(status_msg, f"❌ Ошибка: {str(e)}")


async def reindex_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id if user else None):
        await update.callback_query.answer("Доступ запрещён.", show_alert=True)
        return
    query = update.callback_query
    await query.answer()
    repo_name = query.data.split(":", 1)[1]

    await query.edit_message_text(f"🔄 Переиндексирую {repo_name}...")
    status_msg = query.message
    await _run_reindex(status_msg, repo_name)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id if user else None):
        return
    text = "📊 Статус коллекций:\n\n"
    
    collections = rag.list_collections()
    if not collections:
        text += "Нет коллекций."
    else:
        for repo in collections:
            info = rag.get_collection_info(repo)
            text += f"✅ {repo}: {info['vectors_count']} векторов\n"
    
    await update.message.reply_text(text)


# Макс. сообщений в контексте диалога для RAG (user + assistant пары)
_CHAT_HISTORY_LIMIT = 20


def _telegram_html(text: str) -> str:
    """Подготовка текста для Telegram HTML (подмножество Markdown).

    - **жирный** → <b>
    - *курсив* (одна пара звёздочек на строку) → <i>
    - _курсив_ → <i>
    - `код` → <code>, блоки ``` → <pre>
    - Экранирует <, >, & в обычном тексте
    """
    result = []
    i = 0
    
    while i < len(text):
        # Code block: ```...```
        if text.startswith("```", i):
            end = text.find("```", i + 3)
            if end != -1:
                code_content = text[i + 3:end]
                result.append(f"<pre>{html_escape(code_content)}</pre>")
                i = end + 3
                continue
        
        char = text[i]
        
        # Inline code: `...`
        if char == "`":
            end = text.find("`", i + 1)
            if end != -1:
                code_content = text[i + 1:end]
                result.append(f"<code>{html_escape(code_content)}</code>")
                i = end + 1
                continue
        
        # Markdown bold: **...**
        if char == "*" and i + 1 < len(text) and text[i + 1] == "*":
            end = text.find("**", i + 2)
            if end != -1:
                bold_content = text[i + 2:end]
                if "\n" not in bold_content:
                    result.append(f"<b>{html_escape(bold_content)}</b>")
                    i = end + 2
                    continue
            result.append("*")
            i += 1
            continue
        
        # Markdown italic: *...* (не в начале строки — маркер списка)
        if char == "*":
            prev_char = text[i - 1] if i > 0 else "\n"
            if prev_char == "\n" or (i == 0):
                result.append("*")
                i += 1
                continue
            end = i + 1
            closing = -1
            while end < len(text):
                if text[end] == "\n":
                    break
                if text[end] == "*":
                    if end + 1 < len(text) and text[end + 1] == "*":
                        end += 2
                        continue
                    closing = end
                    break
                end += 1
            if closing != -1 and closing > i + 1:
                italic_content = text[i + 1:closing]
                result.append(f"<i>{html_escape(italic_content)}</i>")
                i = closing + 1
                continue
            result.append("*")
            i += 1
            continue
        
        # Italic: _..._ (must be on same line)
        if char == "_":
            end = text.find("_", i + 1)
            if end != -1 and end > i + 1:
                italic_content = text[i + 1:end]
                if "\n" not in italic_content:
                    result.append(f"<i>{html_escape(italic_content)}</i>")
                    i = end + 1
                    continue
        
        # Escape special chars
        if char == "&":
            result.append("&amp;")
        elif char == "<":
            result.append("&lt;")
        elif char == ">":
            result.append("&gt;")
        else:
            result.append(char)
        
        i += 1
    
    return "".join(result)


def html_escape(s: str) -> str:
    """Escape HTML special characters."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _is_addressed_to_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """В группах — при упоминании @бот или reply на бота; в личке — всегда."""
    msg = update.effective_message
    if not msg or not msg.text:
        return False
    chat = msg.chat
    if chat.type == ChatType.PRIVATE:
        return True
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
        return False
    bot = context.bot
    bot_username = (bot.username or "").lower()
    text = (msg.text or "").lower()
    # Простая проверка @username (UTF-16 в entities ломает срез для эмодзи/кириллицы)
    if f"@{bot_username}" in text:
        return True
    # Reply на сообщение бота — тоже обращение
    if msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.id == bot.id:
        return True
    return False


def _extract_question(text: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Убирает упоминание бота из текста сообщения."""
    bot_username = (context.bot.username or "").lower()
    return re.sub(rf"\s*@{re.escape(bot_username)}\s*", " ", text, flags=re.IGNORECASE).strip()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = msg.chat if msg else None
    txt = (msg.text or "")[:80] if msg else ""
    logger.info("handle_message: chat=%s type=%s user_id=%s text=%r", chat.id if chat else None, getattr(chat, "type", None), user.id if user else None, txt)
    if not is_allowed(user.id if user else None):
        logger.info("handle_message: skip whitelist user_id=%s", user.id if user else None)
        return
    if not _is_addressed_to_bot(update, context):
        logger.info("handle_message: skip not addressed chat_type=%s", chat.type if chat else None)
        return
    question = _extract_question(msg.text, context)

    if question.startswith("/") or not question:
        logger.info("handle_message: skip empty/question")
        return

    qerr = validate_user_question(question)
    if qerr:
        await msg.reply_text(qerr)
        return

    status_queue = queue.Queue()
    steps: list[str] = ["🤔 Думаю..."]

    def on_qdrant_status(text: str):
        status_queue.put(text)
        steps.append(text)

    status_msg = await msg.reply_text("🤔 Думаю...")

    history = list(context.chat_data.get("history", []))[-_CHAT_HISTORY_LIMIT:]
    t0 = time.monotonic()
    answer = None
    session_data = {}
    loop = asyncio.get_event_loop()

    try:
        def run_rag():
            if state.settings.rag_mode == "simple":
                return rag.generate_simple_answer(
                    question,
                    repo_name=None,
                    top_k=state.settings.top_k,
                    max_chunks=state.settings.max_chunks,
                    model=state.settings.model,
                    temperature=state.settings.temperature,
                    on_status=on_qdrant_status,
                )
            return rag.generate_answer(
                question, history=history, on_status=on_qdrant_status
            )

        future = loop.run_in_executor(None, run_rag)
        while not future.done():
            try:
                line = status_queue.get_nowait()
                await _safe_edit_text(status_msg, line)
            except queue.Empty:
                pass
            await asyncio.sleep(0.15)
        answer, session_data = future.result()
        status_text = "✅ Готово."
        usage = session_data.get("usage") or {}
        pt, ct, tt = usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens")
        if (pt or 0) > 0 or (ct or 0) > 0:
            status_text = f"✅ Готово. Вход: {pt or 0:,} ток., выход: {ct or 0:,} ток., всего: {(tt or (pt or 0) + (ct or 0)):,}"
        await _safe_edit_text(status_msg, status_text)
        steps.append(status_text)
        formatted = _telegram_html(answer)
        try:
            await msg.reply_text(formatted, parse_mode=ParseMode.HTML)
        except BadRequest:
            await msg.reply_text(answer)
        # Дополняем историю для следующих вопросов
        h = context.chat_data.setdefault("history", [])
        h.append({"role": "user", "content": question})
        h.append({"role": "assistant", "content": answer})
        context.chat_data["history"] = h[-_CHAT_HISTORY_LIMIT:]
    except Exception as e:
        answer = f"❌ Ошибка: {str(e)}"
        await msg.reply_text(answer)
    finally:
        save_session({
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "telegram",
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "question": question,
            "answer": answer,
            "duration_s": round(time.monotonic() - t0, 2),
            "steps": steps,
            **session_data,
            "rag_mode": state.settings.rag_mode,
        })


def is_allowed(user_id: int | None) -> bool:
    if not config.TELEGRAM_WHITELIST_USERS:
        return True
    return user_id is not None and str(user_id) in config.TELEGRAM_WHITELIST_USERS


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update and update.message:
        await update.message.reply_text(f"Произошла ошибка: {context.error}")
