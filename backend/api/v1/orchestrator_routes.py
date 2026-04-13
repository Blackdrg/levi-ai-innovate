"""
Sovereign Orchestration Routes v15.0-GA.
Separated mission dispatch and telemetry from basic chat services.
"""

import logging
import json
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orchestrator", tags=["Cognitive Orchestration"])

class MissionRequest(BaseModel):
    message: str = Field(..., description="Sovereign OS query")
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)

@router.post("/mission")
async def dispatch_mission_v15(
    request: MissionRequest,
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Atomic High-Fidelity Mission Dispatch (v15.0.0).
    Hardened for Tier 2 Regional Hybrid execution.
    """
    uid = getattr(identity, "uid", "guest")
    logger.info(f"[Orchestrator-v15] Mission dispatch triggered: {uid}")
    
    try:
        from backend.main import orchestrator
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator offline.")

        mission_res = await orchestrator.handle_mission(
            user_input=request.message,
            user_id=uid,
            session_id=request.session_id,
            context=request.context,
            priority=request.priority,
            simplicity_mode=False # Full DAG execution
        )
        
        return {
            "mission_id": mission_res.get("request_id"),
            "status": mission_res.get("status", "accepted"),
            "mode": mission_res.get("mode"),
            "timestamp": f"{uuid.uuid1()}" # Sovereign v15 trace ID
        }
    except Exception as e:
        logger.error(f"[Orchestrator-v15] Mission Dispatch Anomaly: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mission/{mission_id}")
async def get_mission_status(
    mission_id: str,
    identity: Any = Depends(get_sovereign_identity)
):
    """Retrieves current execution state of a mission."""
    uid = getattr(identity, "uid", "guest")
    from backend.main import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator offline.")
    
    state = await orchestrator.get_mission(mission_id, uid)
    if not state:
        raise HTTPException(status_code=404, detail="Mission not found in cluster state.")
    
    return state

@router.get("/chat/stream")
async def orchestrate_stream_v15(
    q: str,
    session_id: Optional[str] = None,
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Streaming Sovereign Mission (v15.0.0 SSE).
    Directly initiates a cognitive stream and yields tokens from the swarm.
    """
    uid = getattr(identity, "uid", "guest")
    logger.info(f"[Orchestrator-v15] SSE stream pulse requested: {uid}")

    from backend.main import orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator offline.")

    async def _event_wrapper():
        try:
            generator = await orchestrator.handle_mission(
                user_input=q,
                user_id=uid,
                session_id=session_id or f"sess_{uuid.uuid4().hex[:8]}",
                streaming=True,
                simplicity_mode=False
            )
            async for chunk in generator:
                yield f"event: {chunk.get('event', 'message')}\ndata: {json.dumps(chunk['data']) if isinstance(chunk.get('data'), (dict, list)) else chunk.get('data', '')}\n\n"
            
            yield "event: end\ndata: [STREAM_COMPLETE]\n\n"
        except Exception as e:
            logger.error(f"[Orchestrator-v15] Stream anomaly: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(_event_wrapper(), media_type="text/event-stream")
