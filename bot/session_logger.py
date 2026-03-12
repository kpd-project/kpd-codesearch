import json
from datetime import datetime
from pathlib import Path

import config

LOGS_DIR = Path(__file__).parent.parent / "logs"


def save_session(session: dict) -> None:
    """Сохраняет JSON-сессию и удаляет устаревшие файлы сверх LOG_ROTATION."""
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = LOGS_DIR / f"session_{ts}.json"
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    _rotate()


def _rotate() -> None:
    files = sorted(LOGS_DIR.glob("session_*.json"))
    limit = config.LOG_ROTATION
    for f in files[: max(0, len(files) - limit)]:
        f.unlink(missing_ok=True)
