import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
import uuid
from datetime import datetime
import os

from backend.models import ChatMessage, _INJECTION_PATTERNS
from backend.auth import get_current_user_optional
from backend.redis_client import get_conversation, save_conversation, is_rate_limited
from backend.firestore_db import update_analytics
from backend.payments import use_credits
from backend.generation import generate_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("")
async def chat_endpoint(
    request: Request,
    msg: ChatMessage,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host}"
    user_tier = current_user.get("tier", "free") if current_user else "free"

    if is_rate_limited(str(user_id), limit=10, window=60):
        raise HTTPException(status_code=429, detail="Too many messages. Please wait.")

    msg_low = msg.message.lower()
    if any(pattern in msg_low for pattern in _INJECTION_PATTERNS):
        raise HTTPException(status_code=400, detail="Possible prompt injection detected.")

    from backend.redis_client import get_daily_ai_spend, incr_daily_ai_spend
    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily AI usage limit reached.")
    incr_daily_ai_spend(1.0)

    update_analytics("chats_count")
    history = get_conversation(msg.session_id)

    try:
        response = await generate_response(
            msg.message,
            history=history,
            mood=msg.mood or "philosophical",
            user_tier=user_tier
        )
    except Exception as e:
        logger.error(f"[Chat] Generation failed: {e}")
        raise HTTPException(status_code=500, detail="AI generation failed.")

    history.append({"user": msg.message, "bot": response, "timestamp": datetime.utcnow().isoformat()})
    save_conversation(msg.session_id, history, user_id=user_id)

    return {"response": response, "session_id": msg.session_id}
