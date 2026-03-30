from fastapi import APIRouter, Depends, HTTPException, Request
from backend.utils.exceptions import LEVIException
from typing import Optional
import logging

from backend.models import ChatMessage
from backend.auth import get_current_user_optional
from .engine import run_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Orchestrator"])

@router.post("")
async def orchestrator_endpoint(
    request: Request,
    msg: ChatMessage,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Entry point for the AI Orchestrator via API."""
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host}"
    user_tier = current_user.get("tier", "free") if current_user else "free"
    
    try:
        response = await run_orchestrator(
            user_input=msg.message,
            session_id=msg.session_id,
            user_id=str(user_id),
            user_tier=user_tier,
            mood=msg.mood or "philosophical"
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Orchestration failure: {e}", exc_info=True)
        raise LEVIException("Internal Orchestration Error", status_code=500, error_code="ORCHESTRATION_FAIL")
