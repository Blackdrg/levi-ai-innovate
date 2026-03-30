from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from backend.utils.exceptions import LEVIException
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
import logging
import json
import asyncio

from backend.models import ChatMessage, _INJECTION_PATTERNS
from backend.auth import get_current_user_optional
from backend.redis_client import is_rate_limited, incr_daily_ai_spend, get_daily_ai_spend
from backend.firestore_db import update_analytics
from backend.services.orchestrator import run_orchestrator
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat"])

async def message_generator(orchestrator_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """Simulates streaming for Orchestrator responses."""
    response_text = orchestrator_data.get("response", "")
    metadata = {k: v for k, v in orchestrator_data.items() if k != "response"}
    
    words = response_text.split(" ")
    for i, word in enumerate(words):
        chunk = {
            "choices": [{"delta": {"content": word + (" " if i < len(words)-1 else "")}}],
            "metadata": metadata if i == 0 else {} # Send metadata with first chunk
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.01)
    yield "data: [DONE]\n\n"

@router.post("")
async def chat_endpoint(
    request: Request,
    msg: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host if request.client else '127.0.0.1'}"
    user_tier = current_user.get("tier", "free") if current_user else "free"

    if is_rate_limited(str(user_id), limit=15, window=60):
        raise LEVIException("Too many messages. Please wait.", status_code=429, error_code="RATE_LIMIT_EXCEEDED")

    msg_low = msg.message.lower()
    if any(pattern in msg_low for pattern in _INJECTION_PATTERNS):
        raise HTTPException(status_code=400, detail="Invalid message content.")

    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise LEVIException("Daily AI limit reached.", status_code=429, error_code="DAILY_LIMIT_REACHED")
    
    # --- Orchestrator Integration ---
    # Now returns a Dict with metadata
    orch_result = await run_orchestrator(
        user_input=msg.message,
        session_id=msg.session_id,
        user_id=str(user_id),
        background_tasks=background_tasks,
        user_tier=user_tier,
        mood=msg.mood or "philosophical"
    )

    if request.headers.get("accept") == "text/event-stream" or msg.stream:
        return StreamingResponse(message_generator(orch_result), media_type="text/event-stream")

    return orch_result # Return full metadata (response, intent, job_ids, etc.)

