"""
Sovereign Chat API v8.
Unified conversational interface for the LEVI-AI Sovereign OS.
Bridges to the V8 GraphExecutor and SovereignGenerator (Council of Models).
"""

import logging
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.core.v8.brain import LeviBrainCoreController

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat V8"])

# Initialize the v9.8.1 Brain Controller
brain = LeviBrainCoreController()

class ChatMessage(BaseModel):
    message: str = Field(..., description="The user's conversational input")
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@router.post("")
async def conversational_endpoint(
    request: ChatMessage,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Mission: 100% Deterministic-First Cognitive Route.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[Chat-V8] Routing mission to Brain: {user_id}")
    
    try:
        # Route through the Cognitive Monolith
        response_data = await brain.route(
            user_input=request.message,
            user_id=user_id,
            session_id=session_id,
            streaming=False,
            **(request.context or {})
        )
        return response_data
    except Exception as e:
        logger.error(f"[Chat-V8] Mission failure: {e}")
        raise HTTPException(status_code=500, detail="Neural resonance breach.")

@router.post("/stream")
async def conversational_stream_endpoint(
    request: ChatMessage,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Mission Stream: SSE-based Cognitive Pipeline.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[Chat-V8] Routing streaming mission to Brain: {user_id}")

    async def _mission_generator():
        try:
            # Route through the Cognitive Monolith (Streaming Pass)
            async for chunk in brain.route(
                user_input=request.message,
                user_id=user_id,
                session_id=session_id,
                streaming=True,
                **(request.context or {})
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[Chat-V8] Stream failure: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(_mission_generator(), media_type="text/event-stream")
