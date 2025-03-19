from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessageChunk
from .graph import workflow
from .auth import decode_token, get_current_user
import json
import time
import os
from redis import Redis
from redis.exceptions import ConnectionError
import traceback
from backend.orchestrator_agent.orchestrator import Orchestrator

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_tokens: dict[WebSocket, str] = {}
        
        # Try to connect to Redis if URL is provided
        redis_url = os.getenv("REDIS_URL")
        self.redis = None
        if redis_url:
            try:
                self.redis = Redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
            except (ConnectionError, Exception) as e:
                print(f"Redis connection failed, using in-memory storage: {str(e)}")
                self.redis = None

    async def connect(self, websocket: WebSocket, token: str = None):
        await websocket.accept()
        connection_id = str(id(websocket))
        
        if self.redis:
            if token:
                self.redis.hset("ws_tokens", connection_id, token)
            self.redis.sadd("ws_connections", connection_id)
        else:
            self.active_connections.append(websocket)
            if token:
                self.connection_tokens[websocket] = token

    def disconnect(self, websocket: WebSocket):
        connection_id = str(id(websocket))
        
        if self.redis:
            self.redis.hdel("ws_tokens", connection_id)
            self.redis.srem("ws_connections", connection_id)
        else:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            if websocket in self.connection_tokens:
                del self.connection_tokens[websocket]

    def get_token(self, websocket: WebSocket) -> Optional[str]:
        connection_id = str(id(websocket))
        
        if self.redis:
            return self.redis.hget("ws_tokens", connection_id)
        return self.connection_tokens.get(websocket)

    async def send_message(self, message: str, websocket: WebSocket, message_type: str = "message"):
        await websocket.send_json({
            "type": message_type,
            "content": message,
            "sender": "assistant"
        })

manager = ConnectionManager()

async def verify_token(websocket: WebSocket) -> bool:
    """Verify the token for a websocket connection"""
    token = manager.get_token(websocket)
    if not token:
        return False
    try:
        user = await get_current_user(token)
        return user #bool(user)
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return False

async def handle_chat(websocket: WebSocket, user_message: str, message_type: str = "message", 
                    sector: str = "", check_size: str = "", geographical_location: str = ""):
    """Handle individual chat messages and stream responses"""
    user = await verify_token(websocket)
    if not user:
        await websocket.close(code=4001)
        return
        
    config = {"configurable": {"thread_id": user.username}}
    
    # Parse the message JSON if it's a valid JSON
    user_content = user_message
    current_sector = sector 
    current_check_size = check_size
    current_geo_location = geographical_location
    is_init_reasoning = False
    
    try:
        # First try to parse the entire received message
        data = json.loads(user_message)
        if isinstance(data, dict):
            if data.get("type") == "message" and data.get("content"):
                # This is a standard WebSocket message format
                msg_data = json.loads(data.get("content", "{}"))
                if isinstance(msg_data, dict):
                    # Extract content and parameters
                    user_content = msg_data.get("content", user_message)
                    current_sector = msg_data.get("sector", sector)
                    current_check_size = msg_data.get("check_size", check_size)
                    current_geo_location = msg_data.get("geographical_location", geographical_location)
                    
                    # Check if this is an initialization message
                    if user_content == "init_reasoning":
                        is_init_reasoning = True
                        print("DEBUG - Detected init_reasoning message")
            else:
                # This could be a direct message JSON
                user_content = data.get("content", user_message)
                current_sector = data.get("sector", sector)
                current_check_size = data.get("check_size", check_size)
                current_geo_location = data.get("geographical_location", geographical_location)
    except json.JSONDecodeError:
        # Not a JSON, use as is
        pass
    
    # Create the appropriate message based on type
    if is_init_reasoning:
        # Use a silent system message for initialization
        message = HumanMessage(content="")
    elif message_type == "question_answer":
        message = HumanMessage(content=f"Answer: {user_content}")
    else:
        message = HumanMessage(content=user_content)
    
    # Send typing indicator only for regular messages
    if not is_init_reasoning:
        await manager.send_message("", websocket, "typing")
    
    prev_state = workflow.get_state(config).values
    print('PREVIOUS STATE', prev_state)
    try:
        # Debug: Log the state we're about to send
        print(f"DEBUG - Sending state with: sector={current_sector}, check_size={current_check_size}, geo={current_geo_location}")
        
        # Explicitly set reasoning_completed to False for initialization or first message
        reasoning_completed = prev_state.get("reasoning_completed", False) if prev_state else False
        if is_init_reasoning or not prev_state or "urls" not in prev_state or not prev_state.get("urls"):
            reasoning_completed = False
            print("DEBUG - Setting reasoning_completed to False to trigger reasoning agent")
        
        initial_state = {   
            "messages": [message],
            "sector": current_sector,
            "check_size": current_check_size,
            "geographical_location": current_geo_location,
            "reasoning_completed": reasoning_completed
        }
        
        print(f"DEBUG - Initial state: {initial_state}")
        
        astream = workflow.astream(
            initial_state,
            config=config,
            stream_mode="messages"
        )

        # For initialization messages, don't send stream responses to client
        if is_init_reasoning:
            async for message, metadata in astream:
                if not isinstance(message, AIMessageChunk):
                    print(f"DEBUG - Received non-chunk message during initialization: {type(message)}, {message}")
            
            final_state = workflow.get_state(config).values
            print(f"DEBUG - Final state after initialization: {final_state}")
            
            # Send a silent acknowledgment
            await websocket.send_json({
                "type": "system_message",
                "content": "Initialization complete",
                "sender": "system"
            })
            return
            
        # For regular messages, handle streaming as usual
        message_id = str(int(time.time() * 1000))
        first_chunk = True
        chunks_received = 0
        
        async for message, metadata in astream:
            if isinstance(message, AIMessageChunk) and metadata["langgraph_node"] == Orchestrator.name:
                chunks_received += 1
                if first_chunk:
                    await websocket.send_json({
                        "type": "stream_start",
                        "message_id": message_id,
                        "content": message.content,
                        "sender": "assistant"
                    })
                    first_chunk = False
                else:
                    await websocket.send_json({
                        "type": "stream_chunk",
                        "message_id": message_id,
                        "content": message.content,
                        "sender": "assistant"
                    })
            else:
                # Debug: Log non-AIMessageChunk messages
                print(f"DEBUG - Received non-chunk message: {type(message)}, {message}")
        
        # Debug: Check the final state after processing
        final_state = workflow.get_state(config).values
        print(f"DEBUG - Final state after processing: {final_state}")
        
        if chunks_received == 0:
            await websocket.send_json({
                "type": "message",
                "content": "I'm processing your request. Please let me know if you have any questions.",
                "sender": "assistant"
            })
        else:
            await websocket.send_json({
                "type": "stream_end",
                "message_id": message_id,
                "sender": "assistant"
            })
    except Exception as e:
        print(f"Error in handle_chat: {str(e)}")
        print(f"DEBUG - Exception traceback: {traceback.format_exc()}")
        await websocket.send_json({
            "type": "message",
            "content": "I apologize, but I'm having trouble processing your request. Could you please try again?",
            "sender": "assistant"
        })

async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint that handles connections and messages"""
    try:
        await manager.connect(websocket)
        authenticated = False
        # Store the parameters when received from the frontend
        sector = ''
        check_size = ''
        geographical_location = ''
        
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle authentication message
                if not authenticated and data.get("type") == "auth":
                    token = data.get("token")
                    
                    if token == "test":
                        authenticated = True
                        manager.connection_tokens[websocket] = "test"
                        await websocket.send_json({
                            "type": "auth_success",
                            "sender": "system"
                        })
                        await websocket.send_json({
                            "type": "greeting",
                            "content": "Hello! How can I help you today?",
                            "sender": "assistant"
                        })
                        continue
                    
                    try:
                        if token and token.startswith("Bearer: "):
                            token = token[8:]
                        
                        user = await get_current_user(token)
                        if not user:
                            await websocket.close(code=4001)
                            return
                        
                        authenticated = True
                        manager.connection_tokens[websocket] = token
                        await websocket.send_json({
                            "type": "auth_success",
                            "sender": "system"
                        })
                        await websocket.send_json({
                            "type": "greeting",
                            "content": "Hello! How can I help you today?",
                            "sender": "assistant"
                        })
                        continue
                        
                    except Exception as e:
                        await websocket.close(code=4001)
                        return
                
                # Require authentication for all other messages
                if not authenticated:
                    await websocket.close(code=4001)
                    return
                
                # Handle initialization data
                if data.get("type") == "init_data":
                    sector = data.get("sector", "")
                    check_size = data.get("check_size", "")
                    geographical_location = data.get("geographical_location", "")
                    continue
                
                # Handle ping messages
                if data.get("type") == "ping":
                    continue
                elif data.get("type") == "question_answer":
                    await handle_chat(websocket, message, message_type="question_answer", sector=sector, check_size=check_size, geographical_location=geographical_location)
                    continue
                
                # Check if the message includes sector and other parameters
                if data.get("sector"):
                    sector = data.get("sector", "")
                    check_size = data.get("check_size", "")
                    geographical_location = data.get("geographical_location", "")
                
                # Pass the stored parameters to handle_chat
                await handle_chat(websocket, message, sector=sector, check_size=check_size, geographical_location=geographical_location)
                
            except json.JSONDecodeError:
                if not authenticated:
                    await websocket.close(code=4001)
                    return
                await handle_chat(websocket, message, sector=sector, check_size=check_size, geographical_location=geographical_location)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        try:
            await manager.send_message(str(e), websocket, "error")
        except:
            pass
        manager.disconnect(websocket)