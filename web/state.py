"""In-memory state management for web UI."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import logging
from qdrant_client import QdrantClient
import config

logger = logging.getLogger(__name__)


@dataclass
class Repository:
    """Repository state."""
    name: str
    path: str
    enabled: bool = True
    chunks: int = 0
    last_indexed: str | None = None
    status: str = "idle"  # idle, indexing, error


@dataclass
class RuntimeSettings:
    """Runtime configurable settings."""
    model: str = config.OPENROUTER_MODEL
    temperature: float = 0.1
    top_k: int = 10
    max_chunks: int = 10


class State:
    """Global application state."""

    def __init__(self):
        self.repos: dict[str, Repository] = {}
        self.settings = RuntimeSettings()
        self.qdrant_status: str = "disconnected"
        self.qdrant_client: QdrantClient | None = None
        self.start_time = datetime.now()
        self.indexing_progress: dict[str, int] = {}

    def get_qdrant(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self.qdrant_client is None:
            self.qdrant_client = QdrantClient(
                url=config.QDRANT_URL,
                api_key=config.QDRANT_API_KEY,
            )
        return self.qdrant_client

    def check_qdrant(self) -> bool:
        """Check Qdrant connection."""
        try:
            client = self.get_qdrant()
            client.get_collections()
            self.qdrant_status = "connected"
            return True
        except Exception as e:
            logger.warning(f"Qdrant connection failed: {e}")
            self.qdrant_status = "error"
            return False

    def load_repos_from_qdrant(self):
        """Load repositories from Qdrant collections."""
        try:
            client = self.get_qdrant()
            collections = client.get_collections().collections
            
            # Clear and rebuild
            self.repos.clear()
            
            for col in collections:
                name = col.name
                # Try to get collection info for chunk count
                try:
                    info = client.get_collection(name)
                    chunks = info.points_count
                except:
                    chunks = 0
                
                self.repos[name] = Repository(
                    name=name,
                    path="",  # Path not stored in Qdrant
                    enabled=True,
                    chunks=chunks,
                )
            
            # Add whitelisted repos that don't exist yet
            for repo_name in config.REPOS_WHITELIST:
                if repo_name not in self.repos:
                    self.repos[repo_name] = Repository(
                        name=repo_name,
                        path=str(config.REPOS_BASE_PATH / repo_name),
                        enabled=True,
                        chunks=0,
                    )
                    
        except Exception as e:
            logger.error(f"Failed to load repos from Qdrant: {e}")

    def get_repo(self, name: str) -> Repository | None:
        """Get repository by name."""
        return self.repos.get(name)

    def add_repo(self, name: str, path: str) -> Repository:
        """Add new repository."""
        repo = Repository(name=name, path=path, enabled=True)
        self.repos[name] = repo
        return repo

    def remove_repo(self, name: str) -> bool:
        """Remove repository."""
        if name in self.repos:
            del self.repos[name]
            return True
        return False

    def update_indexing_progress(self, repo: str, progress: int):
        """Update indexing progress."""
        self.indexing_progress[repo] = progress
        if repo in self.repos:
            self.repos[repo].status = "indexing"

    def complete_indexing(self, repo: str, chunks: int):
        """Mark indexing as complete."""
        self.indexing_progress.pop(repo, None)
        if repo in self.repos:
            self.repos[repo].chunks = chunks
            self.repos[repo].status = "idle"
            self.repos[repo].last_indexed = datetime.now().isoformat()

    def error_indexing(self, repo: str):
        """Mark indexing as error."""
        self.indexing_progress.pop(repo, None)
        if repo in self.repos:
            self.repos[repo].status = "error"


# Global state instance
state = State()
