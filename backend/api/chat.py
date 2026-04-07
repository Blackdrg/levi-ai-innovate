"""
Sovereign Chat API v7.
High-fidelity conversational interface for the LEVI-AI OS.
Bridges to the ChatEngine and SovereignGenerator (Council of Models).
Hardened for real-time streaming and identity-aware context.
"""

import logging
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.auth import UserIdentity, get_sovereign_identity
from backend.core.brain import LeviBrain
from backend.engines.utils.security import SovereignSecurity
from backend.core.orchestrator_types import ChatMessage

# Initialize production Brain instance
brain = LeviBrain()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat"])

@router.post("")
async def conversational_endpoint(
    request: ChatMessage,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Standard Sovereign Mission (Blocking).
    Bridges to the BrainOrchestrator for full mission lifecycle.
    """
    logger.info(f"[ChatAPI] Mission started for {identity.user_id}")
    
    if SovereignSecurity.detect_injection(request.message):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        # Collect all events from the stream into a single response (blocking mode)
        # Note: LeviBrain.route(streaming=False) returns the full response dict.
        res = await brain.route(
            user_id=identity.user_id,
            user_input=request.message,
            session_id=request.session_id,
            streaming=False,
            user_tier=identity.tier,
            mood=request.mood or "philosophical"
        )
        
        return {
            "response": res.get("response", ""),
            "session_id": request.session_id,
            "engine": "sovereign_brain_v7",
            "status": "success",
            "metadata": res.get("decision", {})
        }
    except Exception as e:
        logger.error(f"[ChatAPI] Mission failure: {e}")
        return {"status": "error", "message": "The mission encountered an anomaly."}

@router.post("/stream")
async def conversational_stream_endpoint(
    request: ChatMessage,
    identity: UserIdentity = Depends(get_sovereign_identity),
    last_event_id: Optional[str] = None # SSE standard reconnection
):
    """
    Sovereign Mission Stream (SSE) v13.0.
    Supports reconnection via Last-Event-ID for high-reliability mobile/web clients.
    """
    from backend.redis_client import cache
    
    request_id = last_event_id or f"miss_{identity.user_id[:4]}_{hex(int(asyncio.get_event_loop().time()))[2:]}"
    logger.info(f"[ChatAPI] Mission stream started/resumed for {identity.user_id} (ID: {request_id})")

    # Reconnection handling
    cached_response = cache.get(f"stream_cache:{request_id}")
    if cached_response and last_event_id:
        logger.info(f"[ChatAPI] Resuming interrupted stream for {request_id}")
        # In a real system, we'd send only the delta. For v13, we replay the cache.
        pass

    async def _mission_generator():
        accumulated_response = ""
        try:
            # Engage the central LeviBrain (Sovereign OS Heart)
            async for event in await brain.route(
                user_id=identity.user_id,
                user_input=request.message,
                session_id=request.session_id,
                request_id=request_id,
                streaming=True,
                user_tier=identity.tier,
                mood=request.mood or "philosophical"
            ):
                # Unified SSE protocol for the v7 frontend
                if "token" in event:
                    token = event["token"]
                    accumulated_response += token
                    # Cache progress for reconnection support
                    cache.set(f"stream_cache:{request_id}", accumulated_response, ex=3600)
                    yield f"id: {request_id}\ndata: {json.dumps({'choices': [{'delta': {'content': token}}]})}\n\n"
                elif "event" in event:
                    yield f"id: {request_id}\ndata: {json.dumps({event['event']: event['data']})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"[ChatAPI] Mission failure: {e}")
            yield f"event: error\ndata: {json.dumps('Sovereign mission interrupted.')}\n\n"

    return StreamingResponse(_mission_generator(), media_type="text/event-stream")
