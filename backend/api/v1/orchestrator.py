"""
Sovereign Orchestration Gateway v14.0.0.
Primary v1 REST/SSE interface for the Sovereign OS.
"""

import logging
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Graduated v13.0 Core & Identity
from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.core.v8.brain import LeviBrainCoreController
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestrator v13"])

# Unified v14.0.0 Sovereign OS Fabric
brain_gateway = LeviBrainCoreController()

class MissionRequest(BaseModel):
    message: str = Field(..., description="Sovereign OS query")
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)

@router.post("/chat")
async def orchestrate_chat_v14(
    request: MissionRequest,
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Standard Sovereign Chat (v15.0.0) - Synchronous.
    """
    uid = getattr(identity, "uid", "guest")
    logger.info(f"[Orchestrator-v15] Chat mission started: {uid}")
    
    if SovereignSecurity.detect_injection(request.message):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        from backend.main import orchestrator
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator offline.")
            
        res = await orchestrator.handle_mission(
            user_input=request.message,
            user_id=uid,
            session_id=request.session_id,
            context=request.context,
            simplicity_mode=True # Chat uses simplicity mode by default
        )
        
        return {
            "response": res.get("response", ""),
            "status": "success",
            "request_id": res.get("request_id")
        }
    except Exception as e:
        logger.error(f"[Orchestrator-v15] Chat Anomaly: {e}")
        return {"status": "error", "message": "Sovereign OS synchronization drift."}


# Remaining routes are now managed in orchestrator_routes.py
