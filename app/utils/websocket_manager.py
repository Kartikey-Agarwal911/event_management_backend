from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected to WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def broadcast_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                    logger.debug(f"Sent message to user {user_id}: {message}")
                except WebSocketDisconnect:
                    self.disconnect(connection, user_id)

    async def notify_event_created(self, user_id: int, event: dict):
        """Send notification when an event is created"""
        await self.broadcast_to_user(user_id, {
            "type": "event_created",
            "event": event
        })

    async def notify_event_shared(self, user_id: int, event_id: int):
        """Send notification when an event is shared"""
        await self.broadcast_to_user(user_id, {
            "type": "event_shared",
            "event_id": event_id
        })

# Create a single instance of the connection manager
manager = ConnectionManager() 