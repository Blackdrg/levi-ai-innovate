"""
Sovereign Orchestration Gateway v13.0.0.
Primary entry point for the LEVI-AI OS Sovereign OS.
Bridges to the v13.0 GraphExecutor and MetaPlanner via LeviBrainCoreController.
"""

import logging
import uuid
import json
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.postgres_db import get_read_session

from backend.api.utils.auth import get_current_user
from backend.engines.brain.orchestrator import orchestrator as brain_orchestrator
from backend.engines.utils.security import SovereignSecurity
from sqlalchemy import text
from backend.utils.audit import AuditLogger
from backend.utils.runtime_tasks import create_tracked_task, is_shutting_down

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestration v22"])

class MissionRequest(BaseModel):
    input: str = Field(..., description="The high-level user mission or query")
    session_id: Optional[str] = Field(None, description="The session tracking ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional mission constraints")

@router.post("/mission", status_code=202)
async def orchestrate_mission_endpoint(
    request: MissionRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Mission: Thinking-Loop Orchestration (v22.1).
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    mission_id = f"mission_{uuid.uuid4().hex[:12]}"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    if is_shutting_down():
        raise HTTPException(status_code=503, detail="Runtime is draining in-flight missions.")
    
    logger.info(f"[Orchester-v22] Thinking Mission {mission_id} received for {user_id}")
    
    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    # Dispatch to the Cognitive thinking loop
    async def _run_loop():
        # Using the streaming logic internally but capturing final output for the task
        final_res = ""
        async for chunk in brain_orchestrator.stream_request(user_id, request.input):
            if "token" in chunk:
                final_res += chunk["token"]
            elif chunk.get("event") == "metadata" and chunk.get("data", {}).get("status") == "completed":
                # Mission complete
                pass
        
        # Log to audit or persistence if needed
        logger.info(f"[Orchester-v22] Mission {mission_id} finished logic.")

    create_tracked_task(_run_loop(), name=f"thinking-mission:{mission_id}")
    
    return {
        "status": "ACCEPTED",
        "mission_id": mission_id,
        "session_id": session_id
    }

@router.get("/mission/{mission_id}")
async def get_mission_status(
    mission_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Status Polling (v13.0.0).
    Checks the status of an asynchronous mission.
    """
    if not HAS_REDIS:
        raise HTTPException(status_code=503, detail="Sovereign Redis Link unavailable.")
    
    data = redis_client.get(f"mission:{mission_id}")
    if not data:
        # Sovereign OS v14.0.0: Postgres Resonance Fallback
        async with get_read_session() as session:
            try:
                # Query the missions table for finalized state
                query = text("SELECT status, fidelity_score, result, metadata FROM missions WHERE mission_id = :mid")
                result = await session.execute(query, {"mid": mission_id})
                row = result.fetchone()
                if row:
                    return {
                        "mission_id": mission_id,
                        "status": row[0],
                        "fidelity_score": row[1],
                        "result": row[2],
                        "metadata": row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
                    }
            except Exception as e:
                logger.error(f"[Orchester-v13] SQL Fallback failed: {e}")

        raise HTTPException(status_code=404, detail="Mission pulse not found in Redis or SQL.")
    
    return json.loads(data)

@router.post("/mission/stream")
async def orchestrate_mission_stream_endpoint(
    request: MissionRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    High-Fidelity SSE Streaming Mission (v22.1 Sovereign OS).
    Uses the Brain thinking loop directly.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    
    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    async def sse_generator():
        try:
            async for chunk in brain_orchestrator.stream_request(user_id, request.input):
                event_type = chunk.get("event", "message")
                data = json.dumps(chunk.get("data", chunk))
                yield f"event: {event_type}\ndata: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[Orchester-v22] Stream failure: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

class ApprovalRequest(BaseModel):
    mission_id: str
    node_id: str
    decision: str = Field(..., description="Either 'approved' or 'rejected'")
    feedback: Optional[str] = None

@router.post("/mission/approve")
async def approve_mission_node(
    request: ApprovalRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign HITL: Human Approval Signal (v13.0.0).
    Signals the paused Graph Executor to resume or abort.
    """
    if not HAS_REDIS:
        raise HTTPException(status_code=500, detail="Sovereign Redis Link unavailable.")
    
    approval_key = f"hitl:approval:{request.mission_id}:{request.node_id}"
    
    # 1. Verify existence
    if not redis_client.exists(approval_key):
        raise HTTPException(status_code=404, detail="Pending approval pulse not found or expired.")
    
    # 2. Set Signal
    decision = request.decision.lower()
    if decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid decision pulse.")
        
    redis_client.set(approval_key, decision)
    if request.feedback:
        redis_client.set(f"{approval_key}:feedback", request.feedback)
    
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    await AuditLogger.log_event(
        event_type="HITL",
        action="Human Decision",
        user_id=user_id,
        resource_id=request.mission_id,
        status=decision,
        metadata={"node_id": request.node_id, "feedback": request.feedback}
    )
    
    logger.info(f"[HITL] Decision '{decision}' received for mission {request.mission_id}")
    return {"status": "success", "message": f"Mission node {decision}."}
@router.delete("/mission/{mission_id}")
async def cancel_mission_endpoint(
    mission_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Cancellation: Abort an in-flight mission.
    Triggers immediate stop in GraphExecutor and background cleanup.
    """
    from backend.utils.mission import MissionControl
    
    # 1. Verify existence/ownership if possible (omitted for speed in this spec)
    # 2. Set Cancellation Flag
    MissionControl.cancel_mission(mission_id)
    
    # 3. Mark state as FAILED in sm
    from backend.core.execution_state import CentralExecutionState, MissionState
    sm = CentralExecutionState(mission_id)
    sm.transition(MissionState.FAILED)
    
    logger.info(f"[Orchester-v13] Mission {mission_id} cancellation requested by user.")
    return {"status": "success", "message": f"Mission {mission_id} cancellation pulse emitted."}
