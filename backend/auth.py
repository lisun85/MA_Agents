from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel

class AIAssistant(BaseModel):
    assistant_name: str = "AI Assistant"
    assistant_location: str = "Cloud"
    purpose: str = "To assist with questions"

class User(BaseModel):
    username: str
    email: Optional[str] = None
    ai_assistant: AIAssistant = AIAssistant()

async def decode_token(token: str) -> dict:
    """Mock token decoder that treats any token as valid"""
    return {"sub": "test_user"}

async def get_current_user(token: str) -> User:
    """Get the current user from a token"""
    if token == "test":
        # Return mock user for testing
        return User(username="test_user")
    
    try:
        payload = await decode_token(token)
        username = payload.get("sub", "")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return User(username=username)
    except Exception as e:
        print(f"Error authenticating user: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token") from e 