from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from backend.core.perception import PerceptionEngine
from backend.core.memory_manager import MemoryManager
from backend.auth.logic import get_current_user

router = APIRouter(tags=["Perception"])

@router.post("/classify")
async def classify_intent(request: Dict[str, Any], identity: Any = Depends(get_current_user)):
    """
    Sovereign Perception API (v15.0 GA).
    Analyzes user input and extracts structured intent and context.
    """
    text = request.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Text input required.")
    
    uid = getattr(identity, "uid", "guest")
    memory = MemoryManager()
    perception_engine = PerceptionEngine(memory)
    
    # Session ID is optional for standalone classification
    session_id = request.get("session_id", "standalone_perceive")
    
    result = await perception_engine.perceive(
        user_input=text,
        user_id=uid,
        session_id=session_id
    )
    
    return result
