from fastapi import APIRouter, Depends, HTTPException, Request, Response # type: ignore
from typing import Optional, List
import uuid
from datetime import datetime
import os

from backend.models import ChatMessage # type: ignore
from backend.auth import get_current_user_optional  # type: ignore
from backend.redis_client import get_conversation, save_conversation, is_rate_limited  # type: ignore
from backend.firestore_db import update_analytics # type: ignore
from backend.models import ChatMessage, _INJECTION_PATTERNS # type: ignore
from backend.payments import use_credits # type: ignore

router = APIRouter(prefix="/chat", tags=["Chat"], version="3.0.0")

@router.post("")
async def chat_endpoint(
    request: Request,
    msg: ChatMessage,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host}"
    
    # ── Defensive: Rate Limiting ────────────────────────
    if is_rate_limited(str(user_id), limit=10, window=60):
        logger.warning(f"[RateLimit] Throttled user {user_id} in Chat")
        raise HTTPException(status_code=429, detail="Too many chat messages. Please wait a minute.")
    
    # ── Security: Prompt Injection Check ────────────────
    msg_low = msg.message.lower()
    if any(pattern in msg_low for pattern in _INJECTION_PATTERNS):
        logger.warning(f"[Security] Blocked potential prompt injection from user {user_id}")
        raise HTTPException(status_code=400, detail="Possible prompt injection detected.")

    # ── Financial: Credit Check ─────────────────────────
    if user_id:
        try:
            use_credits(str(user_id), 1)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[Chat] Credit deduction failed: {e}")

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
        
        # Phase 44: Real-Time Broadcast (Synthesis Pulse)
        from backend.gateway import broadcast_activity # type: ignore
        broadcast_activity("synthesis_started", {
            "tier": user_tier,
            "session": str(msg.session_id)[:8]
        })
        
        # Async generation with Phase 43 Council of Models for Pro/Creator
        response = await generate_response(
            msg.message, 
            history=history, 
            mood=msg.mood or "philosophical",
            user_tier=user_tier
        )
        
        # Phase 44: Broadcast Completion
        broadcast_activity("synthesis_completed", {
            "tier": user_tier,
            "complexity": len(response)
        })
        
        # Save history
        history.append({"user": msg.message, "bot": response, "timestamp": datetime.utcnow().isoformat()})
        save_conversation(msg.session_id, history, user_id=user_id)
        
        return {"response": response, "history": history}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
