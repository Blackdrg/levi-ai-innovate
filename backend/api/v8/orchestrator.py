"""
Sovereign Orchestration Gateway v9.8.1.
Primary entry point for the LEVI-AI OS Brain.
Bridges to the V9 GraphExecutor and MetaPlanner.
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.core.v8.brain import LeviBrainCoreController
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestration V8"])

# Initialize the v9.8.1 Brain Controller
brain = LeviBrainCoreController()

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
    Sovereign Mission: 100% Deterministic-First Orchestration.
    Unified entry point for the Cognitive Monolith.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[Orchester-V9] Mission received for {user_id}")
    
    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        # Route through the v9.8.1 Brain
        response_data = await brain.route(
            user_input=request.input,
            user_id=user_id,
            session_id=session_id,
            streaming=False,
            **(request.context or {})
        )
        return {
            "status": "success",
            "session_id": session_id,
            **response_data
        }
    except Exception as e:
        logger.error(f"[Orchester-V9] Orchestration failure: {e}")
        return {"status": "error", "message": "Neural protocol drift."}

@router.post("/mission/stream")
async def orchestrate_mission_stream_endpoint(
    request: MissionRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    High-Fidelity SSE Streaming Mission (V9.8.1 Monolith).
    Streams: Perception -> Goal -> Graph -> Execution -> Synthesis.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    async def sse_generator():
        try:
            # Route through the v9.8.1 Brain (Streaming)
            async for chunk in brain.route(
                user_input=request.input,
                user_id=user_id,
                session_id=session_id,
                streaming=True,
                **(request.context or {})
            ):
                # Standardize SSE format: event and data
                event_type = chunk.get("event", "message")
                data = json.dumps(chunk.get("data", chunk))
                yield f"event: {event_type}\ndata: {data}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[Orchester-V9] Stream failure: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

from datetime import datetime, timezone
import uuid

from datetime import datetime, timezone
