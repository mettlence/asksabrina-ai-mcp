from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.mcp.agent import handle_question

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

# Main Chat Endpoint
@app.post("/api/chat", response_model=AnalyticsResponse)
async def chat(request: QuestionRequest):
    """
    Main endpoint for marketing team to ask analytics questions
    
    Example questions:
    - "What's the payment success rate this year?"
    - "Show me trending topics"
    - "What's overall customer sentiment?"
    """
    try:
        answer = handle_question(request.question)
        return AnalyticsResponse(answer=answer, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)