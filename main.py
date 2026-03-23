"""Точка входа: Web UI (FastAPI + uvicorn)."""
import logging
import sys

import uvicorn

from web.main import app as fastapi_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain_community").setLevel(logging.WARNING)


def run_web():
    """Run FastAPI web server."""
    logger.info("Starting Web UI on http://0.0.0.0:8000")
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


def main():
    logger.info("=" * 50)
    logger.info("KPD CodeSearch - Starting Web UI")
    logger.info("=" * 50)
    try:
        run_web()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
