from fastapi import APIRouter, Depends, HTTPException, Request, Response # type: ignore
from typing import Optional, List
import uuid
from datetime import datetime
import os

from backend.models import ChatMessage # type: ignore
from backend.auth import get_current_user_optional # type: ignore
from backend.redis_client import get_conversation, save_conversation # type: ignore
from backend.firestore_db import update_analytics # type: ignore

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("")
async def chat_endpoint(
    request: Request,
    msg: ChatMessage,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = current_user.get("uid") if current_user else None
    
    # ── Cost Protection Layer ──────────────────────────
    from backend.redis_client import get_daily_ai_spend, incr_daily_ai_spend  # type: ignore
    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily AI usage limit reached. Try again tomorrow.")
    incr_daily_ai_spend(1.0)

    # Analytics via transaction
    update_analytics("chats_count")

    # Load history
    history = get_conversation(msg.session_id)

    # Multi-Agent logic (simplified for router)
    try:
        from backend.agents import RouterAgent  # type: ignore
        router_agent = RouterAgent()
        classification = router_agent.classify_intent(msg.message)
        
        # ... logic for response generation (using history, user memory, etc.)
        # For brevity, I'll refer back to the agents implementation
        from backend.generation import generate_response # type: ignore
        response = generate_response(msg.message, history=history, mood=msg.mood or "philosophical")
        
        # Save history
        history.append({"user": msg.message, "bot": response, "timestamp": datetime.utcnow().isoformat()})
        save_conversation(msg.session_id, history, user_id=user_id)
        
        return {"response": response, "history": history}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
