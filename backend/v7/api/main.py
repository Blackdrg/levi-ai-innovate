# Sovereign Architecture Layer: API Core
from fastapi import FastAPI
from pydantic import BaseModel
import sys
import os

# Add the backend directory to path to allow importing engines
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from engines.brain.orchestrator import BrainOrchestrator

app = FastAPI(title="LEVI-AI Sovereign OS API")
brain = BrainOrchestrator()

class QueryRequest(BaseModel):
    user_id: str
    query: str

@app.get("/")
def read_root():
    return {"status": "active", "layer": "api_v7", "brain": "online"}

@app.post("/api/v1/query")
async def handle_query(req: QueryRequest):
    """Primary Brain interface. Routes all operations through the pipeline."""
    state = await brain.process_request(user_id=req.user_id, query=req.query)
    
    return {
        "status": "success" if not state.error else "error",
        "intent": state.intent,
        "response": state.final_response,
        "error": state.error
    }
