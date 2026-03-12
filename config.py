import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WHITELIST_USERS = set(
    u.strip() for u in os.getenv("TELEGRAM_WHITELIST_USERS", "").split(",") if u.strip()
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
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

# Макс. символов в одном батче эмбеддингов (~4 символа ≈ 1 токен)
EMBED_MAX_CHARS_PER_BATCH = int(os.getenv("EMBED_MAX_CHARS_PER_BATCH", "8000"))

# Размер батча для upsert (избежание 413 nginx)
QDRANT_UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "200"))

# Количество последних сессий в logs/ (ротация)
LOG_ROTATION = int(os.getenv("LOG_ROTATION", "10"))
