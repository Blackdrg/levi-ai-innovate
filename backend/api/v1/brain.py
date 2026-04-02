"""
Sovereign Brain API v7.
Strategic intent detection and engine routing for the LEVI-AI OS.
Bridges to the FusionEngine for high-fidelity synthesis.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.auth.models import UserProfile as UserIdentity
from backend.core.brain import LeviBrainV8
from backend.core.fusion_engine import FusionEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Brain"])

# Initialize v8 brain
brain = LeviBrainV8()

class BrainRequest(BaseModel):
    message: str = Field(..., description="The user input to analyze")
    session_id: Optional[str] = None

# Dependency removed as we use get_current_user from auth.logic

@router.post("")
async def brain_strategy_endpoint(
    request: BrainRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    High-fidelity intent detection and strategic synthesis.
    Determines the optimal cognitive path for the OS.
    """
    logger.info(f"[BrainAPI] Strategic analysis started for {identity.user_id}")
    
    try:
        # 1. Strategic Intent Detection (v7 Core)
        intent_data = await detect_intent(request.message)
        
        # 2. Parallel Synthesis (Fusion)
        # We provide an immediate cognitive insight using the FusionEngine
        # and dummy results for a fast pulse
        fusion_result = await FusionEngine.fuse_results(
            query=request.message,
            results=[{"agent": "KNOWLEDGE", "message": "Analyzing multidimensional resonance...", "success": True}],
            lang="en"
        )
        
        return {
            "strategy": intent_data.intent_type,
            "confidence": intent_data.confidence_score,
            "insight": fusion_result,
            "session_id": request.session_id,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"[BrainAPI] Strategic failure: {e}")
        return {"status": "error", "message": "The cosmic brain pulse is out of sync."}
