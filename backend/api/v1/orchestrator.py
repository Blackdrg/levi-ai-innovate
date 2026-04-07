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

@router.post("/chat")
async def orchestrate_mission_v13(
    request: MissionRequest,
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Standard Sovereign Mission (v14.0.0) - Synchronous.
    """
    uid = getattr(identity, "uid", "guest")
    logger.info(f"[Orchestrator-v13] Synchronous mission started: {uid}")
    
    if SovereignSecurity.detect_injection(request.message):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        res = await brain_gateway.run_mission_sync(
            input_text=request.message,
            user_id=uid,
            session_id=request.session_id,
            context=request.context
        )
        
        return {
            "response": res.get("response", ""),
            "intent": res.get("decision", "chat"),
            "fidelity": res.get("fidelity_score", 1.0),
            "status": "success",
            "metadata": {
                 "engine": "sovereign_os_v14.0.0",
                 "latency_ms": res.get("latency_ms")
            }
        }
    except Exception as e:
        logger.error(f"[Orchestrator-v13] Anomaly: {e}")
        return {"status": "error", "message": "Sovereign OS synchronization drift."}

@router.post("/chat/stream")
async def orchestrate_stream_v13(
    request: MissionRequest,
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Streaming Sovereign Mission (v14.0.0 SSE).
    """
    uid = getattr(identity, "uid", "guest")
    logger.info(f"[Orchestrator-v13] SSE mission started: {uid}")

    async def _sovereign_stream():
        try:
            async for event in brain_gateway.run_mission_stream(
                user_input=request.message,
                user_id=uid,
                session_id=request.session_id,
                context=request.context
            ):
                event_type = event.get("event", "data")
                yield f"event: {event_type}\ndata: {json.dumps(event.get('data', event))}\n\n"
            
            yield f"event: done\ndata: {json.dumps('[MISSION_COMPLETE]')}\n\n"
        except Exception as e:
            logger.error(f"[Orchestrator-v13] Stream drift: {e}")
            yield f"event: error\ndata: {json.dumps('Sovereign OS flux.')}\n\n"

    return StreamingResponse(_sovereign_stream(), media_type="text/event-stream")
