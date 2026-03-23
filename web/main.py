"""Web UI server - FastAPI with static files."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from web.api import router as api_router
from web.websocket import ws_manager
from web.state import state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting KPD CodeSearch Web UI...")
    
    # Проверяем подключение к Qdrant (repo-данные хранятся в Qdrant и читаются по запросу)
    state.check_qdrant()
    logger.info(f"Qdrant status: {state.qdrant_status}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="KPD CodeSearch",
    description="Web interface for KPD CodeSearch",
    version="2.0.0",
    lifespan=lifespan,
)

# Dev: фронт на другом origin (Vite :5173) или прямой VITE_API_BASE_URL
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router)


@app.websocket("/ws/state")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await ws_manager.connect(websocket)
    try:
        # Send initial status
        qdrant_ok = state.check_qdrant()
        await ws_manager.send_personal(websocket, {
            "type": "connected",
            "qdrant": state.qdrant_status,
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main page."""
    # Serve from ui/dist (built React app)
    index_path = Path(__file__).parent.parent / "ui" / "dist" / "index.html"
    
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    
    # Fallback: simple HTML if not built
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KPD CodeSearch</title>
        <style>
            body { font-family: system-ui; background: #1a1b26; color: #c0caf5; 
                   display: flex; justify-content: center; align-items: center; 
                   height: 100vh; margin: 0; }
            .container { text-align: center; }
            h1 { color: #7aa2f7; }
            p { color: #565f89; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>KPD CodeSearch Web UI</h1>
            <p>Build the frontend first: <code>cd ui && npm run build</code></p>
            <p>Then restart the server.</p>
        </div>
    </body>
    </html>
    """


# Serve static files from ui/dist — Vite builds with /assets/ and /favicon.svg at root
static_path = Path(__file__).parent.parent / "ui" / "dist"
if static_path.exists():
    assets_path = static_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    # Favicon at root (index.html references /favicon.svg)
    favicon_path = static_path / "favicon.svg"
    if favicon_path.exists():

        @app.get("/favicon.svg")
        async def favicon():
            return FileResponse(str(favicon_path), media_type="image/svg+xml")


_index_path = Path(__file__).parent.parent / "ui" / "dist" / "index.html"

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(request: Request, full_path: str):
    """SPA catch-all: отдаём index.html для любого фронт-роута."""
    if _index_path.exists():
        return HTMLResponse(_index_path.read_text(encoding="utf-8"))
    return HTMLResponse("Not found", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
