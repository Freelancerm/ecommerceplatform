from fastapi import WebSocket
from typing import List, Dict
from ..core.redis_client import redis_client


class ConnectionManager:
    """
    Maintains active WebSocket connections for users and admins and routes messages.
    """

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.admin_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Accepts a user websocket and registers it in local cache and Redis.
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        await redis_client.add_online_user(user_id)

    async def connect_admin(self, websocket: WebSocket):
        """
        Accepts an admin websocket and registers it locally.
        """
        await websocket.accept()
        self.admin_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """
        Safely disconnects a user websocket and updates Redis presence.
        """
        connections = self.active_connections.get(user_id)
        if connections is None:
            return

        if websocket in connections:
            connections.remove(websocket)
        if connections:
            self.active_connections[user_id] = connections
        else:
            self.active_connections.pop(user_id, None)
            await redis_client.remove_online_user(user_id)

    async def disconnect_admin(self, websocket: WebSocket):
        """
        Safely disconnects an admin websocket.
        """
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)

    async def send_personal_message(self, message: str, user_id: str):
        """
        Sends a message to all websocket connections owned by a user.
        """
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except RuntimeError:
                    # Connection might be dead
                    pass

    async def broadcast_admin(self, message: str):
        """
        Broadcasts a message to all connected admins.
        """
        for connection in self.admin_connections:
            try:
                await connection.send_text(message)
            except RuntimeError:
                pass


manager = ConnectionManager()
