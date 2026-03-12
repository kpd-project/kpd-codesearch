from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid
import time
import config
from .chunker import get_all_chunks
from .embeddings import get_embeddings
from .qdrant_client import get_client, create_collection



def index_repo(repo_name: str, verbose: bool = True) -> dict:
    t0 = time.perf_counter()
    log = lambda s: print(s) if verbose else None

    repo_path = config.REPOS_BASE_PATH / repo_name
    if not repo_path.exists():
        return {"error": f"Repository not found: {repo_name}"}

    if repo_name not in config.REPOS_WHITELIST:
        return {"error": f"Repository not in whitelist: {repo_name}"}

    log(f"\n[reindex] {repo_name}")
    create_collection(repo_name)

    t1 = time.perf_counter()
    chunks = get_all_chunks(repo_name)
    if not chunks:
        return {"error": "No code files found"}

    indexed_paths = sorted({c["metadata"]["path"] for c in chunks})
    files_count = len(indexed_paths)
    log(f"  scan   {files_count} files → {len(chunks)} chunks  ({time.perf_counter() - t1:.1f}s)")
    if verbose:
        for p in indexed_paths:
            log(f"    + {p}")

    embeddings = get_embeddings()
    client = get_client()

    # repo/path префикс в тексте эмбеддинга — иначе поиск по имени файла и репо не работает.
    # В payload сохраняется только content.
    texts = [f"{c['metadata']['repo']}/{c['metadata']['path']}\n{c['content']}" for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    n = len(texts)

    t2 = time.perf_counter()
    vectors = []
    idx = 0
    batch_no = 0
    while idx < n:
        batch_texts = []
        batch_chars = 0
        while idx < n and (batch_chars + len(texts[idx])) <= config.EMBED_MAX_CHARS_PER_BATCH:
            batch_texts.append(texts[idx])
            batch_chars += len(texts[idx])
            idx += 1
        if not batch_texts:
            batch_texts.append(texts[idx])
            batch_chars = len(texts[idx])
            idx += 1
        vecs = embeddings.embed_documents(batch_texts)
        vectors.extend(vecs)
        batch_no += 1
        log(f"  embed  batch {batch_no}  {idx}/{n} vectors  (~{batch_chars // 1000}k chars)")
    log(f"  embed  done {n} vectors  ({time.perf_counter() - t2:.1f}s)")

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "content": text,
                **metadata
            }
        )
        for text, vector, metadata in zip(texts, vectors, metadatas)
    ]

    t3 = time.perf_counter()
    batch_size = config.QDRANT_UPSERT_BATCH_SIZE
    log(f"  upsert uploading {len(points)} points (batch={batch_size})...")
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=repo_name, points=batch)
        log(f"  upsert batch {i // batch_size + 1}  {min(i + batch_size, len(points))}/{len(points)}")
    log(f"  upsert ✓  ({time.perf_counter() - t3:.1f}s)")
    log(f"  done   {time.perf_counter() - t0:.1f}s total\n")

    return {
        "repo": repo_name,
        "chunks": len(chunks),
        "vectors": len(vectors),
    }
