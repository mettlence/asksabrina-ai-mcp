import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.mcp.agent import handle_question
from src.models.conversation import ConversationRequest, ConversationResponse, Message
from src.services.conversation_store import conversation_store
from collections import defaultdict

mode_usage = defaultdict(int)
tool_usage = defaultdict(int)

app = FastAPI(
    title="MCP Analytics API",
    description="Marketing Analytics Chat API for Demographics Data",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://sudo.asksabrina.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class QuestionRequest(BaseModel):
    question: str
    
class AnalyticsResponse(BaseModel):
    answer: str
    status: str = "success"

# Health Check Endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "mcp-analytics-api"
    }

# Limit characters
MAX_QUESTION_LENGTH = 500

# Main Chat Endpoint
@app.post("/api/chat", response_model=ConversationResponse)
async def chat(request: ConversationRequest):
    """
    Conversational endpoint with memory
    
    Set use_agentic=true for GPT-powered tool orchestration
    """

    # Limit input characters
    if len(request.question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Question too long. Max {MAX_QUESTION_LENGTH} characters."
        )
    

    try:
        conv_id = request.conversation_id or str(uuid.uuid4())
        stored_history = conversation_store.get_history(conv_id, last_n=10)
        history = request.history if request.history else stored_history
        
        # Handle question (with agentic mode support)
        answer, metadata = handle_question(
            request.question, 
            history=history,
            use_agentic=request.use_agentic
        )
        
        # Store conversation
        new_messages = [
            Message(role="user", content=request.question),
            Message(role="assistant", content=answer, metadata=metadata)
        ]
        conversation_store.add_messages(conv_id, new_messages)
        
        return ConversationResponse(
            answer=answer,
            conversation_id=conv_id,
            metadata=metadata,
            status="success"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Agentic Chat Mode
@app.post("/api/chat/agentic")
async def chat_agentic(request: ConversationRequest):
    """
    Agentic mode endpoint - GPT decides all tool calls
    More flexible but slower than standard mode
    """
    # Limit input characters
    if len(request.question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Question too long. Max {MAX_QUESTION_LENGTH} characters."
        )
    
    request.use_agentic = True
    return await chat(request)

# Info Endpoint
@app.get("/")
async def root():
    return {
        "message": "MCP Analytics API v1.0",
        "endpoints": {
            "chat": "/api/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.post("/api/debug/intent")
async def debug_intent(request: QuestionRequest):
    """
    Debug endpoint to see how intent detection works
    Shows both pattern and semantic matching scores
    """
    try:
        from src.services.hybrid_intent_detector import HybridIntentDetector
        
        detector = HybridIntentDetector()
        explanation = detector.get_intent_explanation(request.question)
        
        return {
            "status": "success",
            "explanation": explanation
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/metrics")
async def get_metrics():
    """View usage metrics"""
    return {
        "mode_usage": dict(mode_usage),
        "tool_usage": dict(tool_usage),
        "total_queries": sum(mode_usage.values())
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)