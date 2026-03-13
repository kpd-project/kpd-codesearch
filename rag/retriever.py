from qdrant_client import QdrantClient
import config
from .embeddings import get_embeddings
from .qdrant_client import get_client, collection_exists


def search_in_repo(repo_name: str, query: str, top_k: int = 5) -> list[dict]:
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
    min_score = config.RAG_MIN_SCORE
    return [
        {
            "content": r.payload.get("content", ""),
            "path": r.payload.get("path", ""),
            "language": r.payload.get("language", ""),
            "type": r.payload.get("type", ""),
            "score": r.score,
        }
        for r in resp.points
        if min_score <= 0 or r.score >= min_score
    ]


def search_all_repos(query: str, top_k: int = 3) -> list[dict]:
    all_results = []
    
    for repo_name in config.REPOS_WHITELIST:
        if collection_exists(repo_name):
            results = search_in_repo(repo_name, query, top_k)
            for r in results:
                r["repo"] = repo_name
            all_results.extend(results)
    
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:config.RAG_SEARCH_ALL_LIMIT]
