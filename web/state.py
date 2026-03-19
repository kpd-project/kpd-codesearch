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
)
from rag.repos_metadata import get_metadata, set_metadata, remove_metadata

logger = logging.getLogger(__name__)

_METADATA_FILE = Path(__file__).parent.parent / "repos_metadata.json"


@dataclass
class RuntimeSettings:
    """Runtime configurable settings."""
    model: str = config.OPENROUTER_MODEL
    temperature: float = 0.1
    top_k: int = 10
    max_chunks: int = 10


class State:
    """Global application state.

    Persistent per-repo данные (path, enabled, description, last_indexed) хранятся
    в Qdrant Collection Properties через REST API.
    Эфемерное (статус индексации) — в памяти.
    """

    def __init__(self):
        self.settings = RuntimeSettings()
        self.qdrant_status: str = "disconnected"
        self.qdrant_client: QdrantClient | None = None
        self.start_time = datetime.now()
        self.indexing_progress: dict[str, int] = {}
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
        return {
            "name": name,
            "path": metadata.get("path") or str(config.REPOS_BASE_PATH / name),
            "enabled": metadata.get("enabled", True),
            "chunks": chunks,
            "last_indexed": metadata.get("last_indexed"),
            "status": self._repo_status.get(name, "idle"),
            "description": metadata.get("description"),
            "embedder_model": props.get("embedder_model"),
            "embedder_dimension": props.get("embedder_dimension"),
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
        set_metadata(name, {"path": path, "enabled": False})
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

    def remove_repo(self, name: str) -> bool:
        """Очищает эфемерный статус. Коллекцию удаляет вызывающий код."""
        self._repo_status.pop(name, None)
        self.indexing_progress.pop(name, None)
        remove_metadata(name)
        return True

    def set_status(self, name: str, status: str):
        self._repo_status[name] = status

    def update_indexing_progress(self, repo: str, progress: int):
        self.indexing_progress[repo] = progress
        self._repo_status[repo] = "indexing"

    def complete_indexing(self, repo: str, chunks: int):
        self.indexing_progress.pop(repo, None)
        self._repo_status.pop(repo, None)
        metadata = get_metadata(repo)
        metadata["last_indexed"] = datetime.now().isoformat()
        set_metadata(repo, metadata)

    def error_indexing(self, repo: str):
        self.indexing_progress.pop(repo, None)
        self._repo_status[repo] = "error"


# Global state instance
state = State()
