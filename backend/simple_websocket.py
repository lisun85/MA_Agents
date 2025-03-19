from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket, message_type: str = "message"):
        await websocket.send_json({
            "type": message_type,
            "content": message,
            "sender": "assistant"
        })

# Create a single connection manager instance
manager = ConnectionManager() 