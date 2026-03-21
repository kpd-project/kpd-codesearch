"""FastAPI endpoints for web UI."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
import httpx
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import config
from bot.session_logger import save_session


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
from rag.qdrant_client import collection_exists, delete_collection
from rag.retriever import search_code
from rag.generator import generate_response

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
        },
        "indexing_progress": state.indexing_progress,
        "uptime": _format_uptime(datetime.now() - state.start_time),
    }


@router.get("/api/repos")
async def list_repos():
    """List all repositories."""
    return {"repos": state.list_repos()}


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
            if collection_exists(name):
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
            chunks = await search_code(
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
    
    await ws_manager.broadcast({
        "type": "settings_updated",
        "settings": {
            "model": state.settings.model,
            "temperature": state.settings.temperature,
            "top_k": state.settings.top_k,
            "max_chunks": state.settings.max_chunks,
        },
    })
    
    return {"status": "ok", "settings": state.settings.__dict__}


@router.post("/api/query")
async def query(request: QueryRequest):
    """RAG query with streaming response."""
    t0 = time.monotonic()

    async def generate():
        parts: list[str] = []
        err: Exception | None = None
        try:
            # Search for relevant chunks
            results = await search_code(
                query=request.message,
                repo_filter=request.repo,
                top_k=state.settings.max_chunks,
            )

            # Generate response
            async for chunk in generate_response(
                query=request.message,
                context_chunks=results,
                model=state.settings.model,
                temperature=state.settings.temperature,
            ):
                parts.append(chunk)
                # Одна строка на событие — иначе переносы в чанке ломают SSE и клиент теряет текст.
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            err = e
            logger.error(f"Query failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            body = "".join(parts)
            if err is not None:
                body = (
                    f"{body}\n\n❌ Ошибка: {err}" if body else f"❌ Ошибка: {str(err)}"
                )
            save_session(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "source": "web",
                    "user_id": None,
                    "username": None,
                    "repo_filter": request.repo,
                    "question": request.message,
                    "answer": body,
                    "duration_s": round(time.monotonic() - t0, 2),
                    "model": state.settings.model,
                }
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
