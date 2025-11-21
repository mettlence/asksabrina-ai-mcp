from typing import List, Dict, Optional
from src.models.conversation import Message
from datetime import datetime, timedelta

class ConversationStore:
    """In-memory conversation storage (upgrade to Redis/MongoDB later)"""
    
    def __init__(self, max_messages_per_conversation=20, ttl_hours=24):
        self.conversations: Dict[str, List[Message]] = {}
        self.max_messages = max_messages_per_conversation
        self.ttl_hours = ttl_hours
        self.last_access: Dict[str, datetime] = {}
    
    def add_messages(self, conversation_id: str, messages: List[Message]):
        """Add messages to conversation history"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        self.conversations[conversation_id].extend(messages)
        
        # Keep only last N messages
        self.conversations[conversation_id] = \
            self.conversations[conversation_id][-self.max_messages:]
        
        self.last_access[conversation_id] = datetime.utcnow()
    
    def get_history(self, conversation_id: str, last_n: int = 10) -> List[Message]:
        """Get recent conversation history"""
        self._cleanup_expired()
        
        if conversation_id not in self.conversations:
            return []
        
        self.last_access[conversation_id] = datetime.utcnow()
        return self.conversations[conversation_id][-last_n:]
    
    def _cleanup_expired(self):
        """Remove conversations older than TTL"""
        cutoff = datetime.utcnow() - timedelta(hours=self.ttl_hours)
        expired = [
            conv_id for conv_id, last_time in self.last_access.items()
            if last_time < cutoff
        ]
        for conv_id in expired:
            del self.conversations[conv_id]
            del self.last_access[conv_id]

# Global instance
conversation_store = ConversationStore()