"""
backend/api/brain.py

Dedicated Brain API for LEVI-AI.
Provides high-speed intent detection and engine routing.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.services.auth.logic import get_current_user_optional
from backend.core.planner import detect_intent
from backend.utils.exceptions import LEVIException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Brain"])

class BrainRequest(BaseModel):
    message: str = Field(..., description="The user input to analyze")
    session_id: Optional[str] = Field(default=None, description="Optional session tracking")

@router.post("")
async def brain_detection_endpoint(
    request: Request,
    payload: BrainRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    High-speed intent detection.
    Returns the predicted route and confidence score.
    """
    try:
        user_input = payload.message
        logger.info("Brain Detection Request: %s", user_input[:50])
        
        # 1. Run the planner's intent detection
        intent_result = await detect_intent(user_input)
        
        # 2. Return consistent format for frontend
        return {
            "route": intent_result.intent_type,
            "confidence": intent_result.confidence_score,
            "complexity": intent_result.complexity_level,
            "cost_weight": intent_result.estimated_cost_weight,
            "request_id": f"brain_{request.state.request_id if hasattr(request.state, 'request_id') else 'direct'}"
        }
        
    except Exception as e:
        logger.error(f"Brain detection failure: {e}")
        raise LEVIException(
            "The cosmic brain could not determine the path.",
            status_code=500,
            error_code="BRAIN_DETECTION_FAIL"
        )
