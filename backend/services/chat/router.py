from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
import logging
from datetime import datetime

from backend.models import ChatMessage, _INJECTION_PATTERNS
from backend.auth import get_current_user_optional
from backend.redis_client import get_conversation, save_conversation, is_rate_limited, incr_daily_ai_spend, get_daily_ai_spend
from backend.firestore_db import update_analytics
from backend.payments import use_credits
from backend.services.orchestrator import run_orchestrator
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("")
async def chat_endpoint(
    request: Request,
    msg: ChatMessage,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host if request.client else '127.0.0.1'}"
    user_tier = current_user.get("tier", "free") if current_user else "free"

    if is_rate_limited(str(user_id), limit=10, window=60):
        raise HTTPException(status_code=429, detail="Too many messages. Please wait.")

    msg_low = msg.message.lower()
    if any(pattern in msg_low for pattern in _INJECTION_PATTERNS):
        raise HTTPException(status_code=400, detail="Invalid message content.")

    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily AI limit reached.")
    incr_daily_ai_spend(1.0)

    update_analytics("chats_count")
    
    # --- Orchestrator Integration ---
    bot_response = await run_orchestrator(
        user_input=msg.message,
        session_id=msg.session_id,
        user_id=str(user_id),
        background_tasks=background_tasks,
        user_tier=user_tier,
        mood=msg.mood or "philosophical"
    )

    return {"response": bot_response}
