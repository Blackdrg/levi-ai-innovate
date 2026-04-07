"""
Sovereign Orchestration Gateway v13.0.0.
Primary entry point for the LEVI-AI OS Absolute Monolith.
Bridges to the v13.0 GraphExecutor and MetaPlanner via LeviBrainCoreController.
"""

import logging
import uuid
import json
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from backend.db.redis import r as redis_client, HAS_REDIS

from backend.api.utils.auth import get_current_user
from backend.core.v8.brain import LeviBrainCoreController
from backend.engines.utils.security import SovereignSecurity
from backend.db.postgres_db import get_read_session
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestration v13"])

# Initialize the v13.0.0 Brain Monolith
brain = LeviBrainCoreController()

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
    Sovereign Mission: Asynchronous Orchestration (v13.0.0).
    Returns 202 Accepted and a mission_id for polling.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    mission_id = f"mission_{uuid.uuid4().hex[:12]}"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[Orchester-v13] Async Mission {mission_id} received for {user_id}")
    
    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    # 1. Initialize mission state in Redis
    if HAS_REDIS:
        state = {
            "mission_id": mission_id,
            "status": "PROCESSING",
            "created_at": str(asyncio.get_event_loop().time())
        }
        redis_client.setex(f"mission:{mission_id}", 3600, json.dumps(state))

    # 2. Dispatch mission to background
    async def _run_and_finalize():
        try:
            response_data = await brain.run_mission_sync(
                input_text=request.input,
                user_id=user_id,
                session_id=session_id,
                mission_id=mission_id, # Pass mission_id for tracking
                **(request.context or {})
            )
            if HAS_REDIS:
                final_state = {
                    "mission_id": mission_id,
                    "status": "FINALIZED",
                    "fidelity_score": response_data.get("fidelity_score", 0.95),
                    "result": response_data.get("response", ""),
                    "metadata": response_data.get("metrics", {})
                }
                redis_client.setex(f"mission:{mission_id}", 3600, json.dumps(final_state))
        except Exception as e:
            logger.error(f"[Orchester-v13] Mission {mission_id} failed: {e}")
            if HAS_REDIS:
                redis_client.setex(f"mission:{mission_id}", 3600, json.dumps({"status": "FAILED", "error": str(e)}))

    asyncio.create_task(_run_and_finalize())
    
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
        # Absolute Monolith v13: Postgres Resonance Fallback
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
    High-Fidelity SSE Streaming Mission (v13.0.0 Absolute Monolith).
    Streams: Perception -> Goal -> Graph -> Execution -> Synthesis.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    async def sse_generator():
        try:
            # Route through the v13.0.0 Brain (Streaming)
            async for chunk in brain.run_mission_stream(
                user_input=request.input,
                user_id=user_id,
                session_id=session_id,
                **(request.context or {})
            ):
                # Standardize SSE format: event and data
                event_type = chunk.get("event", "message")
                data = json.dumps(chunk.get("data", chunk))
                yield f"event: {event_type}\ndata: {data}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[Orchester-v13] Stream failure: {e}")
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
    
    logger.info(f"[HITL] Decision '{decision}' received for mission {request.mission_id}")
    return {"status": "success", "message": f"Mission node {decision}."}
