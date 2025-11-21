from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = None
    metadata: Dict[str, Any] = {}  # Store intent, params, data_type
    
    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)

class ConversationRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    history: List[Message] = []
    use_agentic: bool = False

class ConversationResponse(BaseModel):
    answer: str
    conversation_id: str
    metadata: Dict[str, Any] = {}
    status: str = "success"