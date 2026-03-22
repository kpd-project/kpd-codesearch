import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Whitelist users - поддержка JSON файла + .env fallback
_WHITELIST_FILE = Path(__file__).parent / "whitelist.json"

def _load_whitelist() -> set:
    """Загружает whitelist из JSON файла, fallback - .env."""
    if _WHITELIST_FILE.exists():
        try:
            data = json.loads(_WHITELIST_FILE.read_text(encoding="utf-8"))
            users = set(str(u) for u in data.get("users", []))
            if users:
                logger.info(f"Loaded {len(users)} users from whitelist.json")
                return users
        except Exception as e:
            logger.warning(f"Failed to load whitelist.json: {e}")
    
    # Fallback to .env
    return set(u.strip() for u in os.getenv("TELEGRAM_WHITELIST_USERS", "").split(",") if u.strip())

def _save_whitelist(users: set) -> None:
    """Сохраняет whitelist в JSON файл."""
    try:
        data = {"users": sorted(list(users))}
        _WHITELIST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Saved {len(users)} users to whitelist.json")
    except Exception as e:
        logger.error(f"Failed to save whitelist.json: {e}")
        raise

TELEGRAM_WHITELIST_USERS = _load_whitelist()

# Helpers for runtime whitelist management
def add_whitelist_user(user_id: str) -> bool:
    """Добавляет пользователя в whitelist. Returns True if added."""
    if user_id in TELEGRAM_WHITELIST_USERS:
        return False
    TELEGRAM_WHITELIST_USERS.add(user_id)
    _save_whitelist(TELEGRAM_WHITELIST_USERS)
    return True

def remove_whitelist_user(user_id: str) -> bool:
    """Удаляет пользователя из whitelist. Returns True if removed."""
    if user_id not in TELEGRAM_WHITELIST_USERS:
        return False
    TELEGRAM_WHITELIST_USERS.discard(user_id)
    _save_whitelist(TELEGRAM_WHITELIST_USERS)
    return True

OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-preview")

EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "openai/text-embedding-3-small")
EMBEDDINGS_DIMENSION = int(os.getenv("EMBEDDINGS_DIMENSION", "1536"))

QDRANT_URL = os.getenv("QDRANT_URL", "https://qdrant.gotskin.ru")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

REPOS_BASE_PATH = Path(os.getenv("REPOS_BASE_PATH", "d:/projects"))

CHUNK_SIZE = 1500

# Поведенческая часть системного промпта агента (персона + правила)
# Техническая часть (BOT_CONTEXT) добавляется в generator.py автоматически
_PROMPT_FILE = Path(__file__).parent / "system_prompt.txt"
AGENT_SYSTEM_PROMPT = _PROMPT_FILE.read_text(encoding="utf-8").strip()
CHUNK_OVERLAP = 200

# Макс. размер файла в байтах (больше — плейсхолдер вместо содержимого)
FILE_MAX_SIZE = int(os.getenv("FILE_MAX_SIZE", "2_000_000"))

# Макс. символов в одном батче эмбеддингов (~4 символа ≈ 1 токен)
EMBED_MAX_CHARS_PER_BATCH = int(os.getenv("EMBED_MAX_CHARS_PER_BATCH", "8000"))

# Макс. параллельных запросов к эмбеддингам (rate limiting)
EMBED_MAX_CONCURRENT = int(os.getenv("EMBED_MAX_CONCURRENT", "10"))

# Макс. параллельно обрабатываемых файлов
EMBED_MAX_FILES_CONCURRENT = int(os.getenv("EMBED_MAX_FILES_CONCURRENT", "5"))

# Таймаут HTTP-запроса для эмбеддингов (сек)
EMBED_REQUEST_TIMEOUT = int(os.getenv("EMBED_REQUEST_TIMEOUT", "60"))

# Размер батча для upsert (избежание 413 nginx)
QDRANT_UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "200"))

# Количество последних сессий в logs/ (ротация)
LOG_ROTATION = int(os.getenv("LOG_ROTATION", "10"))

# Режим RAG по умолчанию (переключается через /api/config/runtime и сразу действует для веба и бота)
_r = os.getenv("RAG_RUNTIME_MODE", "agent").strip().lower()
RAG_RUNTIME_MODE: str = _r if _r in ("simple", "agent") else "agent"

# --- RAG Agent (generator.py) ---
# Макс. итераций агентного цикла (поиск → LLM → tool_call → ...)
RAG_AGENT_MAX_ITERATIONS = int(os.getenv("RAG_AGENT_MAX_ITERATIONS", "10"))
# Макс. символов чанка в ответе поиска (0 = без обрезки, передавать полный content)
RAG_CHUNK_DISPLAY_CHARS = int(os.getenv("RAG_CHUNK_DISPLAY_CHARS", "0"))
# Топ-K результатов по умолчанию при вызове search_code
RAG_SEARCH_TOP_K = int(os.getenv("RAG_SEARCH_TOP_K", "10"))
# Верхняя граница top_k (LLM не может запросить больше)
RAG_SEARCH_TOP_K_MAX = int(os.getenv("RAG_SEARCH_TOP_K_MAX", "15"))
# Порог score для включения результата (ниже — отбрасываем, 0 = брать все)
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.5"))
# Макс. результатов при поиске по всем репо (объединённый топ)
RAG_SEARCH_ALL_LIMIT = int(os.getenv("RAG_SEARCH_ALL_LIMIT", "15"))
# max_tokens в цикле агента (с tool_calls)
RAG_AGENT_MAX_TOKENS = int(os.getenv("RAG_AGENT_MAX_TOKENS", "10000"))
# max_tokens для финального ответа без инструментов
RAG_AGENT_FINAL_MAX_TOKENS = int(os.getenv("RAG_AGENT_FINAL_MAX_TOKENS", "3000"))
# temperature для LLM (0–1, меньше = детерминированнее)
RAG_AGENT_TEMPERATURE = float(os.getenv("RAG_AGENT_TEMPERATURE", "0.1"))
# Таймаут HTTP-запросов к OpenRouter (сек)
RAG_AGENT_TIMEOUT = int(os.getenv("RAG_AGENT_TIMEOUT", "60"))
# Длина превью результата tool_call в session log
RAG_LOG_RESULT_PREVIEW_LEN = int(os.getenv("RAG_LOG_RESULT_PREVIEW_LEN", "300"))

# --- Simple mode: Query Rewriting ---
# Быстрая/дешёвая модель для переписывания вопроса пользователя в ключевые слова
# перед векторным поиском (шаг Query Rewriting в generate_simple_answer).
SIMPLE_REWRITE_MODEL = os.getenv("SIMPLE_REWRITE_MODEL", "google/gemini-2.5-flash")

# --- Two-Agent Pipeline ---
# Feature flag: использовать двухагентный пайплайн
USE_TWO_AGENT_PIPELINE = os.getenv("USE_TWO_AGENT_PIPELINE", "true").lower() in ("true", "1", "yes")

# Модель для Analyst (аналитик, планировщик поиска) — дешёвая и быстрая
ANALYST_MODEL = os.getenv("ANALYST_MODEL", "google/gemini-2.5-flash")
ANALYST_TEMPERATURE = float(os.getenv("ANALYST_TEMPERATURE", "0.3"))
ANALYST_MAX_TOKENS = int(os.getenv("ANALYST_MAX_TOKENS", "2000"))
ANALYST_TIMEOUT = int(os.getenv("ANALYST_TIMEOUT", "60"))
ANALYST_HISTORY_LIMIT = int(os.getenv("ANALYST_HISTORY_LIMIT", "20"))

# Модель для Answerer (эксперт, синтез ответа) — "думающая" модель
# Для думающих моделей (o3-mini, claude-3.7-sonnet) используется max_completion_tokens
# вместо max_tokens, чтобы ограничить длину "раздумий".
ANSWERER_MODEL = os.getenv("ANSWERER_MODEL", "openai/o3-mini")
ANSWERER_TEMPERATURE = float(os.getenv("ANSWERER_TEMPERATURE", "0.1"))
ANSWERER_MAX_TOKENS = int(os.getenv("ANSWERER_MAX_TOKENS", "4000"))
# Ограничение "раздумий" для моделей с chain-of-thought (0 = не передавать параметр)
ANSWERER_MAX_REASONING_TOKENS = int(os.getenv("ANSWERER_MAX_REASONING_TOKENS", "2000"))
ANSWERER_TIMEOUT = int(os.getenv("ANSWERER_TIMEOUT", "120"))
ANSWERER_HISTORY_LIMIT = int(os.getenv("ANSWERER_HISTORY_LIMIT", "20"))

# Макс. итераций в двухагентном пайплайне — увеличено для глубокого ресёрча
PIPELINE_MAX_ITERATIONS = int(os.getenv("PIPELINE_MAX_ITERATIONS", "4"))
