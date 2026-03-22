import json
import re
from datetime import datetime
from pathlib import Path

import config

LOGS_DIR = Path(__file__).parent.parent / "logs"

# session_YYYYMMDD_HHMMSS_microseconds.json
SESSION_LOG_NAME_RE = re.compile(r"^session_\d{8}_\d{6}_\d+\.json$")


def is_valid_session_log_filename(name: str) -> bool:
    return bool(name and SESSION_LOG_NAME_RE.match(name))


def save_session(session: dict) -> str:
    """Сохраняет JSON-сессию и удаляет устаревшие файлы сверх LOG_ROTATION. Возвращает имя файла."""
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"session_{ts}.json"
    path = LOGS_DIR / filename
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    _rotate()
    return filename


def _rotate() -> None:
    files = sorted(LOGS_DIR.glob("session_*.json"))
    limit = config.LOG_ROTATION
    for f in files[: max(0, len(files) - limit)]:
        f.unlink(missing_ok=True)
