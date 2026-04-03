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
from backend.engines.chat.generation import SovereignGenerator
from backend.core.v8.executor import GraphExecutor
# Import handle_chat logic or define it locally for the V8 standard
# For now, we bridge to the existing v8-ready logic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat V8"])

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
    Standard Sovereign Mission (Blocking).
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Chat-V8] Mission started for {user_id}")
    
    # In V8, we use the SovereignGenerator directly for pure chat 
    # or the GraphExecutor for complex tasks. Pure chat uses Council.
    generator = SovereignGenerator()
    try:
        response = await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Sovereign OS. Efficient, philosophical, and powerful."},
            {"role": "user", "content": request.message}
        ])
        
        return {
            "response": response,
            "session_id": request.session_id,
            "engine": "sovereign_council_v8",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"[Chat-V8] Generation failure: {e}")
        return {"status": "error", "message": "Neural resonance failure."}

@router.post("/stream")
async def conversational_stream_endpoint(
    request: ChatMessage,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Mission Stream (SSE).
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Chat-V8] Stream mission started for {user_id}")

    async def _mission_generator():
        generator = SovereignGenerator()
        try:
            # Note: Council doesn't natively stream in the same way, but we can simulate/implement
            # For now, we yield the final result to maintain the SSE interface
            response = await generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Sovereign OS."},
                {"role": "user", "content": request.message}
            ])
            yield f"data: {json.dumps({'type': 'token', 'data': response})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[Chat-V8] Stream failure: {e}")
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"

    return StreamingResponse(_mission_generator(), media_type="text/event-stream")
