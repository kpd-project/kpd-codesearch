from urllib.parse import urlparse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import config

_client = None

def get_client() -> QdrantClient:
    global _client
    if _client is None:
        parsed = urlparse(config.QDRANT_URL)
        _client = QdrantClient(
            host=parsed.hostname,
            port=parsed.port or (443 if parsed.scheme == "https" else 80),
            path=parsed.path or None,
            https=parsed.scheme == "https",
            api_key=config.QDRANT_API_KEY,
            timeout=30,
            prefer_grpc=False,
            check_compatibility=False,
        )
    return _client

def collection_exists(collection_name: str) -> bool:
    client = get_client()
    cols = client.get_collections().collections
    return any(getattr(c, "name", None) == collection_name for c in cols)

def create_collection(collection_name: str, vector_size: int = None) -> bool:
    if vector_size is None:
        vector_size = config.EMBEDDINGS_DIMENSION
    client = get_client()
    if collection_exists(collection_name):
        return False
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    return True

def delete_collection(collection_name: str) -> bool:
    client = get_client()
    if not collection_exists(collection_name):
        return False
    client.delete_collection(collection_name=collection_name)
    return True

def get_collection_info(collection_name: str) -> dict:
    client = get_client()
    if not collection_exists(collection_name):
        return None
    info = client.get_collection(collection_name=collection_name)
    vec = getattr(info, "indexed_vectors_count", None)
    return {
        "name": collection_name,
        "vectors_count": vec if (vec is not None and vec > 0) else info.points_count,
        "points_count": info.points_count,
    }

def list_collections() -> list[str]:
    client = get_client()
    return [c.name for c in client.get_collections().collections]

def get_collection_properties(collection_name: str) -> dict:
    """Читает метаданные коллекции из config.metadata."""
    client = get_client()
    try:
        info = client.get_collection(collection_name=collection_name)
        config_obj = getattr(info, "config", None)
        if config_obj:
            metadata = getattr(config_obj, "metadata", None)
            if metadata:
                return dict(metadata)
    except Exception:
        pass
    return {}

def set_collection_properties(collection_name: str, props: dict) -> bool:
    """Обновляет метаданные коллекции через PATCH /collections/{name}."""
    client = get_client()
    try:
        existing = get_collection_properties(collection_name)
        merged = {**existing, **props}
        
        client.update_collection(
            collection_name=collection_name,
            metadata=merged,
        )
        return True
    except Exception:
        return False
