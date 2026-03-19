"""Persistent repo metadata storage (path, enabled, description, last_indexed)."""
import json
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_METADATA_FILE = Path(__file__).parent.parent / "repos_metadata.json"

_metadata: dict[str, dict] = {}


def _load() -> dict[str, dict]:
    global _metadata
    try:
        if _METADATA_FILE.exists():
            with open(_METADATA_FILE, "r", encoding="utf-8") as f:
                _metadata = json.load(f)
            logger.info(f"Loaded metadata for {len(_metadata)} repos")
    except Exception as e:
        logger.warning(f"Failed to load metadata: {e}")
        _metadata = {}
    return _metadata


def _save():
    try:
        with open(_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_metadata, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save metadata: {e}")


def get_metadata(name: str) -> dict:
    if not _metadata:
        _load()
    return _metadata.get(name, {})


def set_metadata(name: str, data: dict):
    if not _metadata:
        _load()
    _metadata[name] = data
    _save()


def get_enabled(name: str) -> bool:
    return get_metadata(name).get("enabled", True)


def set_enabled(name: str, enabled: bool):
    data = get_metadata(name)
    data["enabled"] = enabled
    set_metadata(name, data)


def remove_metadata(name: str):
    if name in _metadata:
        del _metadata[name]
        _save()


_load()
