import asyncio
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
import config
from .embeddings import get_embeddings
from .qdrant_client import get_client, collection_exists, list_collections
from .repos_metadata import get_enabled


def search_in_repo(repo_name: str, query: str, top_k: int = 5, min_score: float | None = None) -> list[dict]:
    if not collection_exists(repo_name):
        return []
    if not get_enabled(repo_name):
        return []

    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)
    
    client = get_client()
    resp = client.query_points(
        collection_name=repo_name,
        query=query_vector,
        limit=top_k,
    )
    threshold = min_score if min_score is not None else config.RAG_MIN_SCORE
    return [
        {
            "content": r.payload.get("content", ""),
            "path": r.payload.get("path", ""),
            "language": r.payload.get("language", ""),
            "type": r.payload.get("type", ""),
            "score": r.score,
        }
        for r in resp.points
        if threshold <= 0 or r.score >= threshold
    ]


def search_all_repos(query: str, top_k: int = 3, min_score: float | None = None) -> list[dict]:
    all_results = []
    
    for repo_name in list_collections():
        if not collection_exists(repo_name):
            continue
        if not get_enabled(repo_name):
            continue
        results = search_in_repo(repo_name, query, top_k, min_score)
        for r in results:
            r["repo"] = repo_name
        all_results.extend(results)
    
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:config.RAG_SEARCH_ALL_LIMIT]


def get_file_from_qdrant(repo_name: str, file_path: str) -> str:
    """Восстанавливает содержимое файла из Qdrant по точному пути.

    Используется как фоллбек когда локальный диск (REPOS_BASE_PATH) недоступен.
    Достает все чанки файла через payload-фильтр по полю path и склеивает их.
    """
    if not collection_exists(repo_name):
        return ""

    client = get_client()
    # Нормализуем путь: убираем ведущий слеш и заменяем Windows-разделители
    normalized_path = file_path.lstrip("/").replace("\\", "/")

    scroll_result = client.scroll(
        collection_name=repo_name,
        scroll_filter=qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="path",
                    match=qdrant_models.MatchValue(value=normalized_path),
                )
            ]
        ),
        limit=200,
        with_payload=True,
        with_vectors=False,
    )

    points = scroll_result[0]
    if not points:
        return ""

    # Очищаем заголовок пути, который добавляет indexer.py в виде "repo/path\n..."
    prefix = f"{repo_name}/{normalized_path}"
    cleaned_parts = []
    for p in points:
        raw = p.payload.get("content", "")
        if raw.startswith(prefix):
            raw = raw[len(prefix):].lstrip("\n")
        cleaned_parts.append(raw)

    return "\n...\n".join(cleaned_parts)


async def search_code(
    query: str,
    repo_filter: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Async поиск для Web API. repo_filter=None — по всем репо."""
    if repo_filter:
        results = await asyncio.to_thread(search_in_repo, repo_filter, query, top_k)
        for r in results:
            r["repo"] = repo_filter
        return results
    return await asyncio.to_thread(search_all_repos, query, top_k)
