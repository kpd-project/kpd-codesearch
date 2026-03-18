"""Global application state. Persistent repo metadata lives in Qdrant collection properties."""
from dataclasses import dataclass
from datetime import datetime
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

logger = logging.getLogger(__name__)


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
        # ephemeral: "idle" | "indexing" | "error" — только для текущей сессии
        self._repo_status: dict[str, str] = {}

    def get_qdrant(self) -> QdrantClient:
        if self.qdrant_client is None:
            # Единый фабричный клиент из rag/ — обход SSL-бага на Windows
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_repo(self, name: str, props: dict, chunks: int) -> dict:
        """Собирает dict репозитория из Qdrant-properties + эфемерного статуса."""
        return {
            "name": name,
            "path": props.get("path") or str(config.REPOS_BASE_PATH / name),
            "enabled": props.get("enabled", True),
            "chunks": chunks,
            "last_indexed": props.get("last_indexed"),
            "status": self._repo_status.get(name, "idle"),
            "description": props.get("description"),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_repos(self) -> list[dict]:
        """Все репозитории: коллекции Qdrant + вайтлист без коллекции."""
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
                result[name] = self._build_repo(name, get_collection_properties(name), chunks)

            # Вайтлист-репо, которых ещё нет в Qdrant
            for repo_name in config.REPOS_WHITELIST:
                if repo_name not in result:
                    result[repo_name] = self._build_repo(repo_name, {}, 0)

            return list(result.values())
        except Exception as e:
            logger.error(f"Failed to list repos: {e}")
            return []

    def get_repo(self, name: str) -> dict | None:
        """Один репо из Qdrant или None если не существует и не в вайтлисте."""
        in_qdrant = collection_exists(name)
        if not in_qdrant and name not in config.REPOS_WHITELIST:
            return None
        chunks = 0
        props: dict = {}
        if in_qdrant:
            try:
                info = self.get_qdrant().get_collection(name)
                chunks = info.points_count or 0
            except Exception:
                pass
            props = get_collection_properties(name)
        return self._build_repo(name, props, chunks)

    def repo_exists(self, name: str) -> bool:
        """Репо известен: есть коллекция в Qdrant или в вайтлисте."""
        return collection_exists(name) or name in config.REPOS_WHITELIST

    def add_repo(self, name: str, path: str) -> dict:
        """Регистрирует репо: создаёт пустую коллекцию и сохраняет path в properties."""
        create_collection(name)  # no-op если уже есть
        set_collection_properties(name, {"path": path, "enabled": True})
        return self._build_repo(name, {"path": path, "enabled": True}, 0)

    def remove_repo(self, name: str) -> bool:
        """Очищает эфемерный статус. Коллекцию удаляет вызывающий код."""
        self._repo_status.pop(name, None)
        self.indexing_progress.pop(name, None)
        return True

    def set_status(self, name: str, status: str):
        self._repo_status[name] = status

    def update_indexing_progress(self, repo: str, progress: int):
        self.indexing_progress[repo] = progress
        self._repo_status[repo] = "indexing"

    def complete_indexing(self, repo: str, chunks: int):
        self.indexing_progress.pop(repo, None)
        self._repo_status.pop(repo, None)
        set_collection_properties(repo, {"last_indexed": datetime.now().isoformat()})

    def error_indexing(self, repo: str):
        self.indexing_progress.pop(repo, None)
        self._repo_status[repo] = "error"


# Global state instance
state = State()
