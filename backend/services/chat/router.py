from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
import logging
from datetime import datetime

from backend.models import ChatMessage, _INJECTION_PATTERNS
from backend.auth import get_current_user_optional
from backend.redis_client import get_conversation, save_conversation, is_rate_limited, incr_daily_ai_spend, get_daily_ai_spend
from backend.firestore_db import update_analytics
from backend.payments import use_credits
from backend.generation import generate_response
import os

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
        raise HTTPException(status_code=400, detail="Invalid message content.")

    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily AI limit reached.")
    incr_daily_ai_spend(1.0)

    update_analytics("chats_count")
    history = get_conversation(msg.session_id)

    bot_response = await generate_response(
        msg.message,
        history=history,
        mood=msg.mood or "philosophical",
        user_tier=user_tier
    )

    history.append({"user": msg.message, "bot": bot_response, "timestamp": datetime.utcnow().isoformat()})
    save_conversation(msg.session_id, history, user_id=user_id)

    return {"response": bot_response}
