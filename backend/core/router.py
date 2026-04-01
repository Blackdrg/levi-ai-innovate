"""
backend/services/orchestrator/router.py

FastAPI router for the LEVI AI Orchestrator endpoint.
Mounted at /api/v1/chat by the gateway.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from backend.utils.exceptions import LEVIException
from backend.services.learning.models import ChatMessage
from backend.auth import get_current_user_optional
from .engine import run_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Orchestrator"])


@router.post("")
async def orchestrator_endpoint(
    request: Request,
    msg: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Central AI chat endpoint — routes through the full LEVI orchestrator pipeline.

    Returns the complete orchestrator payload including:
      - response   : The AI-generated text
      - intent     : Detected intent category
      - route      : Engine used (local / tool / api)
      - session_id : Echo of the session identifier
      - job_ids    : Async job IDs (image gen, etc.)
      - request_id : Unique request trace ID
    """
    # Resolve user identity
    if current_user:
        user_id   = current_user.get("uid", f"guest:{request.client.host}")
        user_tier = current_user.get("tier", "free")
    else:
        host      = request.client.host if request.client else "unknown"
        user_id   = f"guest:{host}"
        user_tier = "free"

    logger.info(
        "Orchestrator request: user=%s tier=%s session=%s",
        user_id, user_tier, msg.session_id,
    )

    try:
        result = await run_orchestrator(
            user_input=msg.message,
            session_id=msg.session_id,
            user_id=str(user_id),
            background_tasks=background_tasks,
            user_tier=user_tier,
            mood=msg.mood or "philosophical",
        )

        logger.info(
            "Orchestrator complete: request_id=%s intent=%s route=%s",
            result.get("request_id"), result.get("intent"), result.get("route"),
        )

        # Return the full result dict — preserves intent, route, job_ids, request_id
        return result

    except Exception as e:
        logger.error("Orchestration failure: %s", e, exc_info=True)
        raise LEVIException(
            "Internal Orchestration Error",
            status_code=500,
            error_code="ORCHESTRATION_FAIL",
        )
