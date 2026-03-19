import asyncio
from pathlib import Path
from qdrant_client.models import PointStruct
import uuid
import time
import json
from typing import Callable, Optional

import config
from .chunker import chunk_file
from .chunker.base import iter_code_files
from .embeddings import get_async_embeddings
from .qdrant_client import get_client, create_collection, set_collection_properties

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


def _save_indexed_paths(repo_name: str, indexed_paths: set):
    p = _state_path(repo_name)
    p.write_text(
        json.dumps({"repo": repo_name, "indexed_paths": sorted(indexed_paths)}, ensure_ascii=False),
        encoding="utf-8",
    )


async def _process_file(
    file_path: Path,
    repo_name: str,
    repo_path: Path,
    embeddings,
    client,
    file_semaphore: asyncio.Semaphore,
    progress_lock: asyncio.Lock,
    indexed_paths: set,
    state_path: Path,
    progress_callback: Optional[Callable],
    current_file_idx: int,
    total_files: int,
) -> tuple[int, int]:
    rel_path = file_path.relative_to(repo_path).as_posix()

    async with file_semaphore:
        chunks = chunk_file(file_path, repo_name, repo_path)

    if not chunks:
        if progress_callback:
            progress_callback(current_file_idx, total_files, rel_path, 0, 0, skipped=True)
        return (0, 0)

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

        vecs = await embeddings.embed_documents_async(batch_texts)
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

    async with progress_lock:
        indexed_paths.add(rel_path)
        _save_indexed_paths(repo_name, indexed_paths)

    if progress_callback:
        progress_callback(current_file_idx, total_files, rel_path, len(chunks), len(vectors), skipped=False)

    return (len(chunks), len(vectors))


async def index_repo_async(
    repo_name: str,
    verbose: bool = True,
    resume: bool = False,
    on_progress: Optional[Callable] = None,
    repo_path_override: Optional[Path] = None,
) -> dict:
    t0 = time.perf_counter()
    log = lambda s: print(s) if verbose else None

    repo_path = Path(repo_path_override) if repo_path_override else (config.REPOS_BASE_PATH / repo_name)
    if not repo_path.exists():
        return {"error": f"Repository not found: {repo_name}"}

    log(f"\n[reindex] {repo_name}")
    create_collection(repo_name)
    set_collection_properties(repo_name, {
        "embedder_model": config.EMBEDDINGS_MODEL,
        "embedder_dimension": config.EMBEDDINGS_DIMENSION,
    })

    state_path = _state_path(repo_name)
    if not resume:
        if state_path.exists():
            state_path.unlink()

    indexed_paths = _load_indexed_paths(repo_name)

    embeddings = get_async_embeddings()
    client = get_client()

    file_list = sorted(iter_code_files(repo_path), key=lambda p: p.relative_to(repo_path).as_posix())
    total_files = len(file_list)

    file_semaphore = asyncio.Semaphore(config.EMBED_MAX_FILES_CONCURRENT)
    progress_lock = asyncio.Lock()

    total_chunks = 0
    total_vectors = 0

    def progress_callback(idx: int, total: int, path: str, chunks: int, vectors: int, skipped: bool):
        if skipped:
            log(f"  skip   [{idx}/{total}] {path} (resume/no chunks)")
        else:
            log(f"  + [{idx}/{total}] {path} → {chunks} chunks")
        if on_progress:
            on_progress(idx, total, path, chunks, vectors, skipped)

    tasks = []
    for fi, file_path in enumerate(file_list):
        rel_path = file_path.relative_to(repo_path).as_posix()

        if rel_path in indexed_paths:
            progress_callback(fi + 1, total_files, rel_path, 0, 0, skipped=True)
            continue

        task = asyncio.create_task(
            _process_file(
                file_path=file_path,
                repo_name=repo_name,
                repo_path=repo_path,
                embeddings=embeddings,
                client=client,
                file_semaphore=file_semaphore,
                progress_lock=progress_lock,
                indexed_paths=indexed_paths,
                state_path=state_path,
                progress_callback=progress_callback,
                current_file_idx=fi + 1,
                total_files=total_files,
            )
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            log(f"  error: {result}")
            continue
        if isinstance(result, tuple):
            total_chunks += result[0]
            total_vectors += result[1]

    elapsed = time.perf_counter() - t0
    log(f"  done   {total_chunks} chunks, {total_vectors} vectors  ({elapsed:.1f}s total)\n")

    return {
        "repo": repo_name,
        "chunks": total_chunks,
        "vectors": total_vectors,
    }


def index_repo(
    repo_name: str,
    verbose: bool = True,
    resume: bool = False,
    on_progress: Optional[Callable] = None,
) -> dict:
    return asyncio.run(index_repo_async(repo_name, verbose, resume, on_progress))


async def index_repository(
    repo_path: str | Path,
    collection_name: str,
    progress_callback: Optional[Callable] = None,
) -> int:
    """Индексация по явному пути и имени коллекции (для Web API)."""
    path = Path(repo_path) if repo_path and str(repo_path).strip() else (config.REPOS_BASE_PATH / collection_name)
    result = await index_repo_async(
        repo_name=collection_name,
        verbose=False,
        resume=False,
        on_progress=progress_callback,
        repo_path_override=path,
    )
    if "error" in result:
        raise ValueError(result["error"])
    return result.get("chunks", 0)