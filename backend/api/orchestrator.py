"""
backend/api/orchestrator.py

Central Orchestrator API - The primary interface for the AI Brain.
Refactored from backend/services/orchestrator/router.py.
"""

import logging
import uuid
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from backend.utils.exceptions import LEVIException
from backend.models import ChatMessage
from backend.auth import get_current_user_optional
from backend.services.orchestrator import run_orchestrator
from backend.utils.robustness import standard_retry

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
    Primary AI interaction endpoint. 
    Routes through the LeviBrain for intent-based multi-engine execution.
    """
    # 1. Resolve Identity
    client_host = request.client.host if request.client else "127.0.0.1"
    if current_user:
        user_id = current_user.get("uid")
        user_tier = current_user.get("tier", "free")
    else:
        user_id = f"guest:{client_host}"
        user_tier = "free"

    logger.info("Brain Request [%s] (Tier: %s)", user_id, user_tier)

    # 2. Execution logic
    try:
        # standard_retry can be applied here to catch transient orchestration failures
        result = await run_orchestrator(
            user_input=msg.message,
            session_id=msg.session_id,
            user_id=str(user_id),
            background_tasks=background_tasks,
            user_tier=user_tier,
            mood=msg.mood or "philosophical",
        )

        logger.info(
            "Brain Sequence Complete [req:%s] (Intent:%s)", 
            result.get("request_id"), result.get("intent")
        )

        return result

    except Exception as e:
        logger.error(f"Brain execution failure: {e}", exc_info=True)
        raise LEVIException(
            "The cosmic brain encountered an anomaly.",
            status_code=500,
            error_code="ORCHESTRATION_FAIL"
        )
