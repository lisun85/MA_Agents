# QuickChat Backend

A FastAPI WebSocket server for the QuickChat application.

## Tech Stack

- Python 3.8+
- FastAPI
- WebSockets
- Uvicorn (ASGI server)

## Features

- WebSocket API for real-time chat
- Connection management
- Simple echo response (easily extendable)

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
python main.py
```

The server will be available at http://localhost:5000 and the WebSocket endpoint at ws://localhost:5000/chat

## API Endpoints

- `GET /` - Health check and API info
- `WebSocket /chat` - WebSocket endpoint for chat communication

## Message Format

Messages are exchanged in the following JSON format:

```json
{
  "id": "unique-uuid",
  "text": "Hello, world!",
  "timestamp": "2023-05-15T12:34:56Z",
  "sender": "user" | "bot"
}
```

## Development

For development with automatic reloading:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

## Integration with Frontend

This backend is designed to work with the QuickChat frontend. The WebSocket endpoint `/chat` matches the frontend configuration. 