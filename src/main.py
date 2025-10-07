from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.mcp.agent import handle_question

app = FastAPI(title="Sabrina MCP API")

class Query(BaseModel):
    question: str

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask")
def ask(query: Query):
    answer = handle_question(query.question)
    return {"answer": answer}
