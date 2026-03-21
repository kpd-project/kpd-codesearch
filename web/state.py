"""Global application state. Persistent repo metadata lives in local JSON file + memory."""
import json as _json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

import config
from qdrant_client import QdrantClient
from rag.qdrant_client import (
    get_client as get_qdrant_client,
    collection_exists,
    create_collection,
    get_collection_properties,
    set_collection_properties,
)
from rag.repos_metadata import get_metadata, set_metadata, remove_metadata

logger = logging.getLogger(__name__)

_METADATA_FILE = Path(__file__).parent.parent / "repos_metadata.json"
_UNSET = object()


def _normalize_relative_path(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return None
    return normalized.lstrip("/")


def _embedder_model_from_sources(props: dict, metadata: dict) -> str | None:
    for v in (props.get("embedder_model"), metadata.get("embedder_model")):
        if v is None or v == "":
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _embedder_dimension_from_sources(props: dict, metadata: dict) -> int | None:
    for source in (props, metadata):
        v = source.get("embedder_dimension")
        if v is None or v == "":
            continue
        try:
            return int(v)
        except (TypeError, ValueError):
            continue
    return None


def _resolve_repo_abs_path(repo_name: str, metadata: dict) -> str:
    """Абсолютный путь, который будет использован при индексации прямо сейчас."""
    rel = _normalize_relative_path(metadata.get("relative_path"))
    if rel:
        return str((config.REPOS_BASE_PATH / rel).resolve())

    legacy_path = metadata.get("path")
    if legacy_path:
        try:
            p = Path(legacy_path)
            if p.is_absolute():
                return str(p.resolve())
        except Exception:
            pass

    return str((config.REPOS_BASE_PATH / repo_name).resolve())


@dataclass
class RuntimeSettings:
    """Runtime configurable settings."""
    model: str = config.OPENROUTER_MODEL
    temperature: float = 0.1
    top_k: int = 10
    max_chunks: int = 10


class State:
    """Global application state.

    Persistent per-repo данные (path, enabled, description, short_description, last_indexed) хранятся
    в Qdrant Collection Properties через REST API.
    Эфемерное (статус индексации) — в памяти.
    """

    def __init__(self):
        self.settings = RuntimeSettings()
        self.qdrant_status: str = "disconnected"
        self.qdrant_client: QdrantClient | None = None
        self.start_time = datetime.now()
        # repo -> { current, total, path, chunks, vectors, skipped }
        self.indexing_progress: dict[str, dict] = {}
        self._repo_status: dict[str, str] = {}

    def get_qdrant(self) -> QdrantClient:
        if self.qdrant_client is None:
            self.qdrant_client = get_qdrant_client()
        return self.qdrant_client

    def check_qdrant(self) -> bool:
        try:
            self.get_qdrant().get_collections()
            self.qdrant_status = "connected"
            return True
        except Exception as e:
            logger.warning(f"Qdrant connection failed: {e}")
            self.qdrant_status = "error"
            return False

    def _build_repo(self, name: str, chunks: int, metadata: dict = None, props: dict = None) -> dict:
        """Собирает dict репозитория из metadata + эфемерного статуса + collection properties."""
        if metadata is None:
            metadata = get_metadata(name)
        if props is None:
            props = get_collection_properties(name)
        relative_path = _normalize_relative_path(metadata.get("relative_path"))
        indexed_path = metadata.get("indexed_path")
        abs_path = _resolve_repo_abs_path(name, metadata)
        return {
            "name": name,
            # display_name — часть локальной metadata (не Qdrant), чтобы его можно было
            # надёжно очищать и обновлять без особенностей PATCH /properties.
            "display_name": metadata.get("display_name"),
            "path": abs_path,
            "relative_path": relative_path,
            "indexed_path": indexed_path,
            "enabled": metadata.get("enabled", True),
            "chunks": chunks,
            "last_indexed": metadata.get("last_indexed"),
            "status": self._repo_status.get(name, "idle"),
            "description": props.get("description") or metadata.get("description"),
            "short_description": props.get("short_description"),
            "embedder_model": _embedder_model_from_sources(props, metadata),
            "embedder_dimension": _embedder_dimension_from_sources(props, metadata),
        }

    def list_repos(self) -> list[dict]:
        """Все репозитории: коллекции Qdrant."""
        try:
            client = self.get_qdrant()
            collections = client.get_collections().collections
            result: dict[str, dict] = {}

            for col in collections:
                name = col.name
                try:
                    info = client.get_collection(name)
                    chunks = info.points_count or 0
                except Exception:
                    chunks = 0
                metadata = get_metadata(name)
                result[name] = self._build_repo(name, chunks, metadata)

            return list(result.values())
        except Exception as e:
            logger.error(f"Failed to list repos: {e}")
            return []

    def get_repo(self, name: str) -> dict | None:
        """Один репо из Qdrant или None если не существует."""
        in_qdrant = collection_exists(name)
        if not in_qdrant:
            return None
        chunks = 0
        if in_qdrant:
            try:
                info = self.get_qdrant().get_collection(name)
                chunks = info.points_count or 0
            except Exception:
                pass
        metadata = get_metadata(name)
        return self._build_repo(name, chunks, metadata)

    def repo_exists(self, name: str) -> bool:
        """Репо известен: есть коллекция в Qdrant."""
        return collection_exists(name)

    def add_repo(self, name: str, path: str) -> dict:
        """Регистрирует репо: создаёт пустую коллекцию и сохраняет metadata."""
        create_collection(name)
        set_collection_properties(name, {
            "description": None,
            "short_description": None,
        })
        relative_path: str | None = None
        try:
            p = Path(path)
            if p.is_absolute():
                try:
                    relative_path = str(p.resolve().relative_to(config.REPOS_BASE_PATH.resolve())).replace("\\", "/")
                except Exception:
                    relative_path = None
            else:
                relative_path = _normalize_relative_path(path)
        except Exception:
            relative_path = _normalize_relative_path(path)

        data: dict = {"enabled": False}
        if relative_path:
            data["relative_path"] = relative_path
        else:
            data["path"] = path
        set_metadata(name, data)
        return self._build_repo(name, 0, get_metadata(name))

    def set_repo_enabled(self, name: str, enabled: bool) -> dict:
        """Update repo enabled state."""
        metadata = get_metadata(name)
        metadata["enabled"] = enabled
        set_metadata(name, metadata)
        chunks = 0
        try:
            info = self.get_qdrant().get_collection(name)
            chunks = info.points_count or 0
        except Exception:
            pass
        return self._build_repo(name, chunks, metadata)

    def set_repo_description(self, name: str, description: str):
        """Update repo description."""
        metadata = get_metadata(name)
        metadata["description"] = description
        set_metadata(name, metadata)
        set_collection_properties(name, {"description": description})

    def set_repo_short_description(self, name: str, short_description: str | None):
        """Update short repo description in Qdrant collection properties."""
        set_collection_properties(name, {"short_description": short_description})

    def update_repo_card(
        self,
        name: str,
        display_name: object = _UNSET,
        short_description: object = _UNSET,
        description: object = _UNSET,
        relative_path: object = _UNSET,
    ) -> dict:
        """Update editable fields in repo card."""
        metadata = get_metadata(name)
        props_update: dict[str, str | None] = {}
        if display_name is not _UNSET:
            if display_name is None:
                metadata.pop("display_name", None)
                # Qdrant properties PATCH может игнорировать null; пустая строка
                # гарантированно "перебивает" предыдущее значение.
                props_update["display_name"] = ""
            else:
                normalized = str(display_name).strip()
                if normalized:
                    metadata["display_name"] = normalized
                    props_update["display_name"] = normalized
                else:
                    metadata.pop("display_name", None)
                    props_update["display_name"] = ""

        if short_description is not _UNSET:
            props_update["short_description"] = None if short_description is None else str(short_description)
        if description is not _UNSET:
            metadata["description"] = "" if description is None else str(description)
            props_update["description"] = metadata["description"]

        if relative_path is not _UNSET:
            if relative_path is None:
                metadata.pop("relative_path", None)
            else:
                normalized_rel = _normalize_relative_path(str(relative_path))
                if normalized_rel:
                    metadata["relative_path"] = normalized_rel
                else:
                    metadata.pop("relative_path", None)
        set_metadata(name, metadata)
        if props_update:
            set_collection_properties(name, props_update)

        chunks = 0
        try:
            info = self.get_qdrant().get_collection(name)
            chunks = info.points_count or 0
        except Exception:
            pass
        return self._build_repo(name, chunks, metadata)

    def remove_repo(self, name: str) -> bool:
        """Очищает эфемерный статус. Коллекцию удаляет вызывающий код."""
        self._repo_status.pop(name, None)
        self.indexing_progress.pop(name, None)
        remove_metadata(name)
        return True

    def set_status(self, name: str, status: str):
        self._repo_status[name] = status

    def update_indexing_progress(self, repo: str, progress: dict):
        self.indexing_progress[repo] = progress
        self._repo_status[repo] = "indexing"

    def complete_indexing(self, repo: str, chunks: int, indexed_path: str | None = None):
        self.indexing_progress.pop(repo, None)
        self._repo_status.pop(repo, None)
        metadata = get_metadata(repo)
        metadata["last_indexed"] = datetime.now().isoformat()
        # Фиксируем эмбедер, с которым был построен индекс (для прозрачности в UI/метаданных).
        metadata["embedder_model"] = config.EMBEDDINGS_MODEL
        metadata["embedder_dimension"] = config.EMBEDDINGS_DIMENSION
        if indexed_path:
            metadata["indexed_path"] = indexed_path
        set_metadata(repo, metadata)
        set_collection_properties(
            repo,
            {
                "embedder_model": config.EMBEDDINGS_MODEL,
                "embedder_dimension": config.EMBEDDINGS_DIMENSION,
            },
        )

    def error_indexing(self, repo: str):
        self.indexing_progress.pop(repo, None)
        self._repo_status[repo] = "error"


# Global state instance
state = State()
