from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class SessionResponse(BaseModel):
    session_id: str
    
class MessageHistory(BaseModel):
    role: str
    content: str
    timestamp: str

class ConversationHistory(BaseModel):
    session_id: str
    messages: List[MessageHistory]

class SessionInfo(BaseModel):
    id: str
    created_at: str
    last_activity: str
    first_message: str
