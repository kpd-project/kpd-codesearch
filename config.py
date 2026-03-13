import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WHITELIST_USERS = set(
    u.strip() for u in os.getenv("TELEGRAM_WHITELIST_USERS", "").split(",") if u.strip()
)

OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-preview")

EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "openai/text-embedding-3-small")
EMBEDDINGS_DIMENSION = int(os.getenv("EMBEDDINGS_DIMENSION", "1536"))

QDRANT_URL = os.getenv("QDRANT_URL", "https://qdrant.gotskin.ru")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

REPOS_BASE_PATH = Path(os.getenv("REPOS_BASE_PATH", "d:/kpd-project"))
REPOS_WHITELIST = [
    r.strip() for r in os.getenv("REPOS_WHITELIST", "").split(",") if r.strip()
]

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

# --- Two-Agent Pipeline ---
# Feature flag: использовать двухагентный пайплайн
USE_TWO_AGENT_PIPELINE = os.getenv("USE_TWO_AGENT_PIPELINE", "true").lower() in ("true", "1", "yes")

# Модель для Analyst (аналитик, планировщик поиска)
ANALYST_MODEL = os.getenv("ANALYST_MODEL", "openrouter/z-ai/glm-4-flash")
ANALYST_TEMPERATURE = float(os.getenv("ANALYST_TEMPERATURE", "0.3"))
ANALYST_MAX_TOKENS = int(os.getenv("ANALYST_MAX_TOKENS", "2000"))
ANALYST_TIMEOUT = int(os.getenv("ANALYST_TIMEOUT", "60"))
ANALYST_HISTORY_LIMIT = int(os.getenv("ANALYST_HISTORY_LIMIT", "20"))

# Модель для Answerer (эксперт, синтез ответа)
ANSWERER_MODEL = os.getenv("ANSWERER_MODEL", "openrouter/z-ai/glm-4-plus")
ANSWERER_TEMPERATURE = float(os.getenv("ANSWERER_TEMPERATURE", "0.1"))
ANSWERER_MAX_TOKENS = int(os.getenv("ANSWERER_MAX_TOKENS", "3000"))
ANSWERER_TIMEOUT = int(os.getenv("ANSWERER_TIMEOUT", "90"))
ANSWERER_HISTORY_LIMIT = int(os.getenv("ANSWERER_HISTORY_LIMIT", "20"))

# Макс. итераций в двухагентном пайплайне
PIPELINE_MAX_ITERATIONS = int(os.getenv("PIPELINE_MAX_ITERATIONS", "2"))
