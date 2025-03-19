from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from pathlib import Path
from backend.websocket import websocket_endpoint

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

# Add WebSocket endpoint
@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Mount the static files (built frontend)
# Get the absolute path of the frontend dist directory relative to either the
# current directory when running as a module or from backend directory
current_file = Path(__file__).resolve()
if current_file.parent.name == 'backend':
    # Running from backend directory
    frontend_dist_path = current_file.parent.parent / "frontend" / "dist"
else:
    # Running as a module from root
    frontend_dist_path = Path("frontend/dist").resolve()

if frontend_dist_path.exists():
    print(f"Frontend dist path found at: {frontend_dist_path}")
    # Mount the assets directory for JS/CSS files
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_path / "assets")), name="assets")
    # Mount the dist directory at root
    app.mount("/", StaticFiles(directory=str(frontend_dist_path), html=True), name="static")
    print("Frontend files mounted successfully")
else:
    print(f"Frontend dist path not found at: {frontend_dist_path}")
    # Add a root route to display an error message if frontend is not available
    @app.get("/", response_class=HTMLResponse)
    async def get_root(request: Request):
        return HTMLResponse(content="<html><body><h1>QuickChat API is running but the frontend build is not available. Run 'pnpm build' in the frontend directory.</h1></body></html>")

# If this file is run directly, start the server
if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or use default 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 