"""
Sovereign Orchestration Gateway v8.
Primary entry point for the LEVI-AI OS Brain.
Bridges to the V8 GraphExecutor and MetaPlanner.
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.core.v8.executor import GraphExecutor
from backend.core.v8.meta_planner import MetaPlanner
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestration V8"])

class MissionRequest(BaseModel):
    input: str = Field(..., description="The high-level user mission or query")
    session_id: Optional[str] = Field(None, description="The session tracking ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional mission constraints")

@router.post("/mission")
async def orchestrate_mission_endpoint(
    request: MissionRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Standard Sovereign Mission (V8 Monolith).
    Unified end-to-end cognitive orchestration.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Orchester-V8] Mission received for {user_id}: {request.input[:50]}")
    
    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        from backend.core.v8.orchestrator_node import SovereignOrchestrator
        orchestrator = SovereignOrchestrator()
        session_id = request.session_id or f"session_{user_id}_{int(asyncio.get_event_loop().time())}"
        
        mission_result = await orchestrator.execute_mission(
            user_input=request.input,
            user_id=user_id,
            session_id=session_id,
            context=request.context or {}
        )
        
        return {
            "status": "success",
            "session_id": session_id,
            "orchestrated_at": str(datetime.now(timezone.utc)),
            **mission_result
        }
    except Exception as e:
        logger.error(f"[Orchester-V8] Orchestration failure: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/mission/stream")
async def orchestrate_mission_stream_endpoint(
    request: MissionRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    High-Fidelity SSE Streaming Mission (V8 Monolith).
    Streams: Perception -> Goal -> Graph -> Tasks -> Synthesis.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    session_id = request.session_id or f"session_{user_id}_{int(asyncio.get_event_loop().time())}"

    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    from backend.core.v8.orchestrator_node import SovereignOrchestrator
    orchestrator = SovereignOrchestrator()

    async def sse_generator():
        async for chunk in orchestrator.execute_mission_streaming(
            user_input=request.input,
            user_id=user_id,
            session_id=session_id,
            context=request.context or {}
        ):
            # Format as standard Server-Sent Event
            event_type = chunk.get("event", "message")
            data = json.dumps(chunk.get("data", chunk))
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

from datetime import datetime, timezone
