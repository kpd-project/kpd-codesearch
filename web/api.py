"""FastAPI endpoints for web UI."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Literal, Optional
import json
import logging
import httpx
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import config


def _format_uptime(delta: timedelta) -> str:
    """Формат: X д Y ч Z мин."""
    total_sec = int(delta.total_seconds())
    days = total_sec // 86400
    rem = total_sec % 86400
    hours = rem // 3600
    minutes = (rem % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days} д")
    if hours or days:
        parts.append(f"{hours} ч")
    parts.append(f"{minutes} мин")
    return " ".join(parts)
from web.state import state
from web.websocket import ws_manager
from rag.indexer import index_repository
from rag.qdrant_client import (
    collection_exists,
    delete_collection,
    filter_preserved_repo_metadata,
    get_collection_properties,
    set_collection_properties,
)
from rag.retriever import semantic_search, search_in_repo_detailed, search_all_repos_detailed
from rag.generator import generate_answer, generate_response, simple_session_metadata
from rag.validation import validate_user_question
import queue

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Models ---

class RepoAdd(BaseModel):
    """Request to add repository."""
    name: str
    path: str


class RuntimeSettingsUpdate(BaseModel):
    """Runtime settings update."""
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    max_chunks: Optional[int] = None
    rag_mode: Optional[Literal["simple", "agent"]] = None


class RepoEnabledUpdate(BaseModel):
    """Toggle repo enabled state."""
    enabled: bool


class RepoCardUpdate(BaseModel):
    """Editable fields in repo card."""
    display_name: Optional[str] = None
    relative_path: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None


class QueryRequest(BaseModel):
    """RAG query request."""
    message: str
    repo: Optional[str] = None  # None = search all


# --- API Endpoints ---

@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/api/status")
async def get_status():
    """Get system status."""
    qdrant_ok = state.check_qdrant()
    
    repos_data = state.list_repos()
    
    return {
        "qdrant": {
            "status": state.qdrant_status,
            "connected": qdrant_ok,
        },
        "repos": repos_data,
        "settings": {
            "model": state.settings.model,
            "temperature": state.settings.temperature,
            "top_k": state.settings.top_k,
            "max_chunks": state.settings.max_chunks,
            "rag_mode": state.settings.rag_mode,
        },
        "indexing_progress": state.indexing_progress,
        "uptime": _format_uptime(datetime.now() - state.start_time),
    }


@router.get("/api/repos")
async def list_repos():
    """List all repositories."""
    return {"repos": state.list_repos()}


@router.get("/api/repos/candidates")
async def list_repo_folder_candidates():
    """Подпапки под REPOS_BASE_PATH для выбора при добавлении репозитория."""
    base = Path(config.REPOS_BASE_PATH)
    if not base.exists():
        raise HTTPException(status_code=404, detail="Базовый путь не существует")
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="Базовый путь не является каталогом")
    try:
        return state.list_repo_folder_candidates()
    except OSError as e:
        logger.warning("repo folder candidates scan failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Не удалось прочитать содержимое базового каталога",
        ) from e


@router.post("/api/repos")
async def add_repo(repo: RepoAdd):
    """Add new repository."""
    if state.repo_exists(repo.name):
        raise HTTPException(status_code=400, detail="Repository already exists")

    new_repo = state.add_repo(repo.name, repo.path)

    await ws_manager.broadcast({
        "type": "repo_added",
        "repo": new_repo["name"],
    })

    return {"status": "ok", "repo": new_repo["name"]}


@router.delete("/api/repos/{name}")
async def remove_repo(name: str):
    """Remove repository."""
    if not state.repo_exists(name):
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        state.get_qdrant().delete_collection(name)
    except Exception as e:
        logger.warning(f"Failed to delete Qdrant collection: {e}")

    state.remove_repo(name)

    await ws_manager.broadcast({
        "type": "repo_removed",
        "repo": name,
    })

    return {"status": "ok"}


@router.patch("/api/repos/{name}/enabled")
async def set_repo_enabled(name: str, body: RepoEnabledUpdate):
    """Enable or disable a repository (affects RAG search)."""
    if not state.repo_exists(name):
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = state.set_repo_enabled(name, body.enabled)

    await ws_manager.broadcast({
        "type": "repo_toggled",
        "repo": name,
        "enabled": body.enabled,
    })

    return {"status": "ok", "enabled": repo["enabled"]}


@router.patch("/api/repos/{name}")
async def update_repo_card(name: str, request: Request, body: RepoCardUpdate):
    """Update editable fields in repository card."""
    if not state.repo_exists(name):
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        raw_payload = await request.json()
        fields_set = set(raw_payload.keys()) if isinstance(raw_payload, dict) else set()
    except Exception:
        fields_set = set()
    update_kwargs: dict = {"name": name}
    if "display_name" in fields_set:
        update_kwargs["display_name"] = body.display_name
    if "short_description" in fields_set:
        update_kwargs["short_description"] = body.short_description
    if "description" in fields_set:
        update_kwargs["description"] = body.description
    if "relative_path" in fields_set:
        update_kwargs["relative_path"] = body.relative_path

    updated = state.update_repo_card(**update_kwargs)

    await ws_manager.broadcast({
        "type": "repo_updated",
        "repo": name,
    })

    return {"status": "ok", "repo": updated}


@router.post("/api/repos/{name}/reindex")
async def reindex_repo(name: str, background_tasks: BackgroundTasks):
    """Reindex repository."""
    repo = state.get_repo(name)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    state.set_status(name, "indexing")
    repo_path = repo["path"]

    await ws_manager.broadcast({"type": "index_start", "repo": name})

    async def run_index():
        try:
            preserved_meta: dict = {}
            if collection_exists(name):
                preserved_meta = filter_preserved_repo_metadata(get_collection_properties(name))
                delete_collection(name)
            def on_file_progress(
                idx: int,
                total: int,
                rel_path: str,
                chunks: int,
                vectors: int,
                skipped: bool,
            ):
                payload = {
                    "current": idx,
                    "total": total,
                    "path": rel_path,
                    "chunks": chunks,
                    "vectors": vectors,
                    "skipped": skipped,
                }
                state.update_indexing_progress(name, payload)
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    return
                loop.create_task(
                    ws_manager.broadcast({
                        "type": "index_progress",
                        "repo": name,
                        "progress": payload,
                    })
                )

            total_chunks = await index_repository(
                repo_path=repo_path,
                collection_name=name,
                progress_callback=on_file_progress,
            )
            if preserved_meta:
                set_collection_properties(name, preserved_meta)
            state.complete_indexing(name, total_chunks, indexed_path=repo_path)
            await ws_manager.broadcast({
                "type": "index_complete",
                "repo": name,
                "chunks": total_chunks,
            })
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            state.error_indexing(name)
            await ws_manager.broadcast({
                "type": "index_error",
                "repo": name,
                "error": str(e),
            })

    background_tasks.add_task(run_index)

    return {"status": "indexing_started", "repo": name}


@router.post("/api/repos/{name}/describe")
async def describe_repo(name: str):
    """Generate AI description for repository based on README/AGENTS or code chunks."""
    repo = state.get_repo(name)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Собираем контекст: сначала README/AGENTS.md из папки репо
    context_parts: list[str] = []
    if repo["path"]:
        for candidate in ("README.md", "AGENTS.md", "readme.md", "README.MD"):
            candidate_path = Path(repo["path"]) / candidate
            try:
                text = candidate_path.read_text(encoding="utf-8", errors="ignore")
                context_parts.append(f"=== {candidate} ===\n{text[:4000]}")
            except (OSError, FileNotFoundError):
                pass

    # Если файлов нет — берём чанки из Qdrant
    if not context_parts:
        try:
            chunks = await semantic_search(
                query="project overview purpose architecture",
                repo_filter=name,
                top_k=10,
            )
            for c in chunks:
                context_parts.append(f"[{c.get('path', '')}]\n{c.get('content', '')}")
        except Exception as e:
            logger.warning(f"Failed to fetch chunks for describe: {e}")

    if not context_parts:
        raise HTTPException(status_code=422, detail="No content available for description generation")

    context = "\n\n".join(context_parts)
    prompt = (
        f"На основе приведённых материалов из репозитория «{name}» "
        "напиши короткое описание проекта (1–2 предложения). "
        "Только суть: что это за проект, какую задачу решает. "
        "Без лишних слов и приветствий.\n\n"
        f"{context[:6000]}"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{config.OPENROUTER_API_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.3,
                },
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"LLM error {resp.status_code}: {resp.text}")

        description = resp.json()["choices"][0]["message"].get("content", "").strip()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LLM request timed out")

    short_description = description.split(".")[0].strip()
    if len(short_description) > 140:
        short_description = short_description[:137].rstrip() + "..."
    if not short_description:
        short_description = description[:140].rstrip()

    state.set_repo_description(name, description)
    state.set_repo_short_description(name, short_description)

    await ws_manager.broadcast({
        "type": "repo_described",
        "repo": name,
        "description": description,
        "short_description": short_description,
    })

    return {"description": description, "short_description": short_description}


@router.get("/api/config/system")
async def get_system_config():
    """Системные настройки (только чтение)."""
    return {
        "qdrant": {
            "url": config.QDRANT_URL,
            "api_key_masked": "•" * 8 if config.QDRANT_API_KEY else "",
            "has_api_key": bool(config.QDRANT_API_KEY),
        },
        "embeddings": {
            "model": config.EMBEDDINGS_MODEL,
            "dimension": config.EMBEDDINGS_DIMENSION,
        },
        "repos": {
            "base_path": str(config.REPOS_BASE_PATH),
        },
        "telegram": {
            "bot_token_masked": "•" * 8 if config.TELEGRAM_BOT_TOKEN else "",
            "has_bot_token": bool(config.TELEGRAM_BOT_TOKEN),
            "whitelist_users": list(config.TELEGRAM_WHITELIST_USERS),
        },
        "openrouter": {
            "url": config.OPENROUTER_API_URL,
            "api_key_masked": "•" * 8 if config.OPENROUTER_API_KEY else "",
            "has_api_key": bool(config.OPENROUTER_API_KEY),
        },
    }


@router.get("/api/config")
async def get_config():
    """Get current configuration."""
    return {
        "settings": {
            "model": state.settings.model,
            "temperature": state.settings.temperature,
            "top_k": state.settings.top_k,
            "max_chunks": state.settings.max_chunks,
            "rag_mode": state.settings.rag_mode,
        }
    }


@router.put("/api/config/runtime")
async def update_runtime_settings(settings: RuntimeSettingsUpdate):
    """Update runtime settings."""
    if settings.model is not None:
        state.settings.model = settings.model
    if settings.temperature is not None:
        state.settings.temperature = settings.temperature
    if settings.top_k is not None:
        state.settings.top_k = settings.top_k
    if settings.max_chunks is not None:
        state.settings.max_chunks = settings.max_chunks
    if settings.rag_mode is not None:
        state.settings.rag_mode = settings.rag_mode

    await ws_manager.broadcast({
        "type": "settings_updated",
        "settings": {
            "model": state.settings.model,
            "temperature": state.settings.temperature,
            "top_k": state.settings.top_k,
            "max_chunks": state.settings.max_chunks,
            "rag_mode": state.settings.rag_mode,
        },
    })
    
    return {"status": "ok", "settings": state.settings.__dict__}


def _sse_chunk_answer(text: str, chunk_size: int = 72) -> list[str]:
    """Разбивает ответ на части для SSE (одна строка JSON на событие)."""
    if not text:
        return [""]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


@router.post("/api/query")
async def query(request: QueryRequest):
    """RAG: простой (поиск + один ответ) или агентный цикл как в Telegram — SSE."""
    qerr = validate_user_question(request.message)
    if qerr:
        raise HTTPException(status_code=400, detail=qerr)

    t0 = time.monotonic()

    if state.settings.rag_mode == "simple":
        async def generate_simple():
            steps: list[str] = ["🤔 Думаю..."]
            try:
                yield f"data: {json.dumps({'type': 'status', 'text': steps[0]}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'status', 'text': '🔍 Ищу фрагменты кода…'}, ensure_ascii=False)}\n\n"
                steps.append("🔍 Ищу фрагменты кода…")

                chunks = await semantic_search(
                    request.message,
                    repo_filter=request.repo,
                    top_k=state.settings.top_k,
                )
                chunks = chunks[: state.settings.max_chunks]

                if not chunks:
                    msg = (
                        "По запросу ничего не найдено в индексе. "
                        "Переформулируйте вопрос или проверьте, что репозитории проиндексированы."
                    )
                    yield f"data: {json.dumps({'content': msg}, ensure_ascii=False)}\n\n"
                    total_s = round(time.monotonic() - t0, 2)
                    steps.append("✅ Готово.")
                    session_data = simple_session_metadata()
                    session_data["model_primary"] = state.settings.model
                    log_entry = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "source": "web",
                        "user_id": None,
                        "username": None,
                        "repo_filter": request.repo,
                        "question": request.message,
                        "answer": msg,
                        "duration_s": total_s,
                        "steps": steps,
                        "tool_calls_count": 0,
                        "rag_mode": state.settings.rag_mode,
                    }
                    log_entry.update(session_data)
                    yield f"data: {json.dumps({'type': 'meta', 'duration_s': total_s, 'usage': {}, 'tool_calls_count': 0, 'session_log': log_entry}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                yield f"data: {json.dumps({'type': 'status', 'text': '✍️ Формирую ответ…'}, ensure_ascii=False)}\n\n"
                steps.append("✍️ Формирую ответ…")

                parts: list[str] = []
                async for piece in generate_response(
                    request.message,
                    chunks,
                    model=state.settings.model,
                    temperature=state.settings.temperature,
                ):
                    parts.append(piece)
                    yield f"data: {json.dumps({'content': piece}, ensure_ascii=False)}\n\n"

                body = "".join(parts)
                total_s = round(time.monotonic() - t0, 2)
                steps.append(f"✅ Готово. {total_s} с.")
                session_data = simple_session_metadata()
                session_data["model_primary"] = state.settings.model
                log_entry = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "source": "web",
                    "user_id": None,
                    "username": None,
                    "repo_filter": request.repo,
                    "question": request.message,
                    "answer": body,
                    "duration_s": total_s,
                    "steps": steps,
                    "tool_calls_count": 0,
                    "rag_mode": state.settings.rag_mode,
                }
                log_entry.update(session_data)
                yield f"data: {json.dumps({'type': 'meta', 'duration_s': total_s, 'usage': {}, 'tool_calls_count': 0, 'session_log': log_entry}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Simple query failed: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate_simple(),
            media_type="text/event-stream",
        )

    loop = asyncio.get_running_loop()
    status_queue: queue.Queue[str] = queue.Queue()
    steps: list[str] = ["🤔 Думаю..."]

    def on_status(text: str):
        status_queue.put(text)
        steps.append(text)

    async def generate():
        parts: list[str] = []
        err: Exception | None = None
        session_data: dict = {}
        try:
            yield f"data: {json.dumps({'type': 'status', 'text': steps[0]}, ensure_ascii=False)}\n\n"

            future = loop.run_in_executor(
                None,
                lambda: generate_answer(
                    request.message,
                    history=None,
                    repo_name=request.repo,
                    on_status=on_status,
                ),
            )

            while not future.done():
                try:
                    while True:
                        line = status_queue.get_nowait()
                        yield f"data: {json.dumps({'type': 'status', 'text': line}, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    pass
                await asyncio.sleep(0.12)

            while True:
                try:
                    line = status_queue.get_nowait()
                    yield f"data: {json.dumps({'type': 'status', 'text': line}, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    break

            answer, session_data = future.result()
            usage = session_data.get("usage") or {}
            tool_calls_count = len(session_data.get("tool_calls") or [])

            for chunk in _sse_chunk_answer(answer or ""):
                parts.append(chunk)
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            total_s = round(time.monotonic() - t0, 2)
            pt, ct, tt = usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens")
            done_line = f"✅ Готово. {total_s} с."
            if (pt or 0) > 0 or (ct or 0) > 0:
                done_line += (
                    f" Вход: {pt or 0:,} ток., выход: {ct or 0:,} ток., всего: {(tt or (pt or 0) + (ct or 0)):,}"
                )
            steps.append(done_line)

            body = "".join(parts)
            log_entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "source": "web",
                "user_id": None,
                "username": None,
                "repo_filter": request.repo,
                "question": request.message,
                "answer": body,
                "duration_s": total_s,
                "steps": steps,
                "tool_calls_count": tool_calls_count,
                "rag_mode": state.settings.rag_mode,
            }
            log_entry.update(session_data)

            yield f"data: {json.dumps({'type': 'meta', 'duration_s': total_s, 'usage': usage, 'tool_calls_count': tool_calls_count, 'session_log': log_entry}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            err = e
            logger.error(f"Query failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


class VectorSearchRequest(BaseModel):
    """Запрос для тестирования векторного поиска."""
    query: str
    repo: Optional[str] = None
    top_k: int = 5
    min_score: Optional[float] = None


@router.post("/api/tests/vector-search")
async def tests_vector_search(request: VectorSearchRequest):
    """Тестовый endpoint: сырой поиск по векторам с полными метаданными чанков."""
    top_k = min(max(1, request.top_k), config.RAG_SEARCH_TOP_K_MAX)
    min_score = request.min_score

    if request.repo:
        chunks = await asyncio.to_thread(
            search_in_repo_detailed, request.repo, request.query, top_k, min_score
        )
    else:
        chunks = await asyncio.to_thread(
            search_all_repos_detailed, request.query, top_k, min_score
        )

    return {
        "chunks": chunks,
        "meta": {
            "query": request.query,
            "repo": request.repo,
            "top_k": top_k,
            "min_score": min_score,
            "total": len(chunks),
            "search_all_limit": config.RAG_SEARCH_ALL_LIMIT if not request.repo else None,
        },
    }
