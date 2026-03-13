from pathlib import Path
from qdrant_client.models import PointStruct
import uuid
import time
import json

import config
from .chunker import chunk_file
from .chunker.base import iter_code_files
from .embeddings import get_embeddings
from .qdrant_client import get_client, create_collection

INDEX_STATE_DIR = Path(__file__).resolve().parent.parent / ".index_state"


def _state_path(repo_name: str) -> Path:
    INDEX_STATE_DIR.mkdir(exist_ok=True)
    return INDEX_STATE_DIR / f"{repo_name}.json"


def _load_indexed_paths(repo_name: str) -> set[str]:
    p = _state_path(repo_name)
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return set(data.get("indexed_paths", []))
    except Exception:
        return set()


def _save_indexed_path(state_path: Path, repo_name: str, rel_path: str, indexed_paths: set):
    indexed_paths.add(rel_path)
    state_path.write_text(
        json.dumps({"repo": repo_name, "indexed_paths": sorted(indexed_paths)}, ensure_ascii=False),
        encoding="utf-8",
    )


def index_repo(
    repo_name: str,
    verbose: bool = True,
    resume: bool = False,
    on_progress=None,
) -> dict:
    t0 = time.perf_counter()
    log = lambda s: print(s) if verbose else None

    repo_path = config.REPOS_BASE_PATH / repo_name
    if not repo_path.exists():
        return {"error": f"Repository not found: {repo_name}"}

    if repo_name not in config.REPOS_WHITELIST:
        return {"error": f"Repository not in whitelist: {repo_name}"}

    log(f"\n[reindex] {repo_name}")
    create_collection(repo_name)

    if not resume:
        state_path = _state_path(repo_name)
        if state_path.exists():
            state_path.unlink()

    indexed_paths = _load_indexed_paths(repo_name)
    state_path = _state_path(repo_name)

    embeddings = get_embeddings()
    client = get_client()

    total_chunks = 0
    total_vectors = 0
    file_list = sorted(iter_code_files(repo_path), key=lambda p: p.relative_to(repo_path).as_posix())

    total_files = len(file_list)
    for fi, file_path in enumerate(file_list):
        rel_path = file_path.relative_to(repo_path).as_posix()
        if rel_path in indexed_paths:
            log(f"  skip   [{fi + 1}/{total_files}] {rel_path} (resume)")
            if on_progress:
                on_progress(fi + 1, total_files, rel_path, total_chunks, total_vectors, skipped=True)
            continue

        chunks = chunk_file(file_path, repo_name, repo_path)
        if not chunks:
            log(f"  skip   [{fi + 1}/{total_files}] {rel_path} (no chunks)")
            if on_progress:
                on_progress(fi + 1, total_files, rel_path, total_chunks, total_vectors, skipped=True)
            continue

        texts = [f"{c['metadata']['repo']}/{c['metadata']['path']}\n{c['content']}" for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        n = len(texts)

        vectors = []
        idx = 0
        while idx < n:
            batch_texts = []
            batch_chars = 0
            while idx < n and (batch_chars + len(texts[idx])) <= config.EMBED_MAX_CHARS_PER_BATCH:
                batch_texts.append(texts[idx])
                batch_chars += len(texts[idx])
                idx += 1
            if not batch_texts:
                batch_texts.append(texts[idx])
                idx += 1
            vecs = embeddings.embed_documents(batch_texts)
            vectors.extend(vecs)

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={"content": texts[i], **metadatas[i]},
            )
            for i, vec in enumerate(vectors)
        ]

        batch_size = config.QDRANT_UPSERT_BATCH_SIZE
        for i in range(0, len(points), batch_size):
            client.upsert(collection_name=repo_name, points=points[i : i + batch_size])

        _save_indexed_path(state_path, repo_name, rel_path, indexed_paths)
        total_chunks += len(chunks)
        total_vectors += len(vectors)
        log(f"  + [{fi + 1}/{total_files}] {rel_path} → {len(chunks)} chunks")
        if on_progress:
            on_progress(fi + 1, total_files, rel_path, total_chunks, total_vectors, skipped=False)

    elapsed = time.perf_counter() - t0
    log(f"  done   {total_chunks} chunks, {total_vectors} vectors  ({elapsed:.1f}s total)\n")

    return {
        "repo": repo_name,
        "chunks": total_chunks,
        "vectors": total_vectors,
    }
