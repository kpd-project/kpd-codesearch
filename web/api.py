"""FastAPI endpoints for web UI."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime

from web.state import state
from web.websocket import ws_manager
from rag.indexer import index_repository
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
    
    repos_data = []
    for repo in state.repos.values():
        repos_data.append({
            "name": repo.name,
            "path": repo.path,
            "enabled": repo.enabled,
            "chunks": repo.chunks,
            "last_indexed": repo.last_indexed,
            "status": repo.status,
        })
    
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
        "uptime": str(datetime.now() - state.start_time),
    }


@router.get("/api/repos")
async def list_repos():
    """List all repositories."""
    return {
        "repos": [
            {
                "name": r.name,
                "path": r.path,
                "enabled": r.enabled,
                "chunks": r.chunks,
                "last_indexed": r.last_indexed,
                "status": r.status,
            }
            for r in state.repos.values()
        ]
    }


@router.post("/api/repos")
async def add_repo(repo: RepoAdd):
    """Add new repository."""
    if repo.name in state.repos:
        raise HTTPException(status_code=400, detail="Repository already exists")
    
    new_repo = state.add_repo(repo.name, repo.path)
    
    # Broadcast update
    await ws_manager.broadcast({
        "type": "repo_added",
        "repo": new_repo.name,
    })
    
    return {"status": "ok", "repo": new_repo.name}


@router.delete("/api/repos/{name}")
async def remove_repo(name: str):
    """Remove repository."""
    if name not in state.repos:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Delete from Qdrant
    try:
        client = state.get_qdrant()
        client.delete_collection(name)
    except Exception as e:
        logger.warning(f"Failed to delete Qdrant collection: {e}")
    
    state.remove_repo(name)
    
    await ws_manager.broadcast({
        "type": "repo_removed",
        "repo": name,
    })
    
    return {"status": "ok"}


@router.post("/api/repos/{name}/reindex")
async def reindex_repo(name: str, background_tasks: BackgroundTasks):
    """Reindex repository."""
    if name not in state.repos:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repo = state.repos[name]
    repo.status = "indexing"
    
    # Broadcast start
    await ws_manager.broadcast({
        "type": "index_start",
        "repo": name,
    })
    
    async def run_index():
        try:
            total_chunks = await index_repository(
                repo_path=repo.path,
                collection_name=name,
                progress_callback=lambda p: ws_manager.broadcast({
                    "type": "index_progress",
                    "repo": name,
                    "progress": p,
                })
            )
            state.complete_indexing(name, total_chunks)
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
    
    async def generate():
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
                yield f"data: {chunk}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
