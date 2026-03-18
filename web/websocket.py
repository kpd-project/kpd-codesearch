"""WebSocket handlers for real-time updates."""
import json
from fastapi import WebSocket
from typing import Set
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and track new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return
        
        data = json.dumps(message)
        # Create list to avoid set modification during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                self.disconnect(connection)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")


# Global WebSocket manager
ws_manager = WebSocketManager()
