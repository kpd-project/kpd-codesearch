from qdrant_client import QdrantClient
import config
from .embeddings import get_embeddings
from .qdrant_client import get_client, collection_exists


def search_in_repo(repo_name: str, query: str, top_k: int = 5, min_score: float | None = None) -> list[dict]:
    if not collection_exists(repo_name):
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
    
    for repo_name in config.REPOS_WHITELIST:
        if collection_exists(repo_name):
            results = search_in_repo(repo_name, query, top_k, min_score)
            for r in results:
                r["repo"] = repo_name
            all_results.extend(results)
    
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:config.RAG_SEARCH_ALL_LIMIT]
