"""
Sovereign Orchestration Gateway v13.0.0.
Primary entry point for the LEVI-AI OS Absolute Monolith.
Bridges to the v13.0 GraphExecutor and MetaPlanner via LeviBrainCoreController.
"""

import logging
import json
import asyncio
import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.core.v8.brain import LeviBrainCoreController
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestration v13"])

# Initialize the v13.0.0 Brain Monolith
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
    Sovereign Mission: 100% Deterministic-First Orchestration (v13.0.0).
    Unified entry point for the Cognitive Monolith.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[Orchester-v13] Mission received for {user_id}")
    
    if SovereignSecurity.detect_injection(request.input):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        # Route through the v13.0.0 Absolute Monolith
        response_data = await brain.run_mission_sync(
            input_text=request.input,
            user_id=user_id,
            session_id=session_id,
            **(request.context or {})
        )
        return {
            "status": "success",
            "session_id": session_id,
            **response_data
        }
    except Exception as e:
        logger.error(f"[Orchester-v13] Orchestration failure: {e}")
        return {"status": "error", "message": "Neural protocol drift detected in Monolith."}

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
