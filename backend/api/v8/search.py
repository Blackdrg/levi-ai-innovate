"""
Sovereign Search API v13.0.0.
Directed factual retrieval and research for the Absolute Monolith.
"""

import logging
import uuid
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.core.v8.brain import LeviBrainCoreController

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Search v13"])

class SearchRequest(BaseModel):
    query: str = Field(..., description="The factual search query")
    session_id: Optional[str] = None

@router.post("")
async def search_endpoint(
    payload: SearchRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Direct Search Interface (v13.0.0).
    Bridges to the unified LeviBrain for deep research orchestration.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Search-v13] Deep research mission for {user_id}")
    
    try:
        # v13.0: Absolute Brain Monolith
        brain = LeviBrainCoreController()
        
        # We wrap the query into a high-fidelity research prompt
        research_input = f"Deep research and provide cross-source facts on: {payload.query}"
        
        # 100% Deterministic Research Sync
        result = await brain.run_mission_sync(
            input_text=research_input,
            user_id=user_id,
            session_id=payload.session_id or f"search_{uuid.uuid4().hex[:6]}"
        )
        
        return {
            "query": payload.query,
            "answer": result.get("response", "No conclusive research fragments found."),
            "mission_id": result.get("mission_id"),
            "decision": result.get("decision"),
            "status": "crystallized_v13"
        }
    except Exception as e:
        logger.error(f"[Search-v13] Research sequence failed: {e}")
        raise HTTPException(status_code=500, detail="Neural search failure.")
