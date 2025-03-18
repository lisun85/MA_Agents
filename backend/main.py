from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Initialize FastAPI application
app = FastAPI(title="QuickChat API", description="WebSocket API for QuickChat")

# Add CORS middleware to allow the frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should specify the exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for active connections
class ConnectionManager:
    def __init__(self):
        # active_connections: WebSocket instance -> user identifier
        self.active_connections: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[websocket] = client_id
        print(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        client_id = self.active_connections.get(websocket)
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            print(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))
    
    async def broadcast(self, message: dict, exclude: Optional[WebSocket] = None):
        for connection in self.active_connections:
            if connection != exclude:
                await connection.send_text(json.dumps(message))


# Create manager instance
manager = ConnectionManager()

# Mount the static files (built frontend)
frontend_dist_path = Path("../frontend/dist")
if frontend_dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_path / "assets")), name="assets")

# Root endpoint - serve the index.html from the frontend build
@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    index_path = frontend_dist_path / "index.html"
    if index_path.exists():
        with open(index_path) as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<html><body><h1>QuickChat API is running but the frontend build is not available. Run 'pnpm build' in the frontend directory.</h1></body></html>")


# WebSocket endpoint - must match 'ws://localhost:8080/chat' used in the frontend
@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    # Generate a unique ID for this connection
    client_id = str(uuid.uuid4())
    
    # Accept the connection
    await manager.connect(websocket, client_id)
    
    try:
        # Send a welcome message
        welcome_message = {
            "id": str(uuid.uuid4()),
            "text": "Welcome to QuickChat! Type a message to begin.",
            "timestamp": datetime.now().isoformat(),
            "sender": "bot"
        }
        await manager.send_personal_message(welcome_message, websocket)
        
        # Message handling loop
        while True:
            # Receive a message from the client
            data = await websocket.receive_text()
            
            # Parse the message
            try:
                message = json.loads(data)
                print(f"Received message from client {client_id}: {message}")
                
                # Echo the message back for now (in a real app, you'd process it)
                response = {
                    "id": str(uuid.uuid4()),
                    "text": f"You said: {message['text']}",
                    "timestamp": datetime.now().isoformat(),
                    "sender": "bot"
                }
                
                # Send response back to the client
                await manager.send_personal_message(response, websocket)
                
            except json.JSONDecodeError:
                print(f"Received invalid JSON from client {client_id}")
                error_response = {
                    "id": str(uuid.uuid4()),
                    "text": "Error: Invalid message format",
                    "timestamp": datetime.now().isoformat(),
                    "sender": "bot"
                }
                await manager.send_personal_message(error_response, websocket)
                
    except WebSocketDisconnect:
        # Handle disconnection
        manager.disconnect(websocket)
    except Exception as e:
        # Handle other exceptions
        print(f"Error with client {client_id}: {str(e)}")
        manager.disconnect(websocket)


# If this file is run directly, start the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 