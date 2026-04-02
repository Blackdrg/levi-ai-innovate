"""
Sovereign Chat API v7.
High-fidelity conversational interface for the LEVI-AI OS.
Bridges to the ChatEngine and SovereignGenerator (Council of Models).
Hardened for real-time streaming and identity-aware context.
"""

import logging
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Sovereign Mission Stream (SSE).
    Real-time multi-agent orchestration via the Brain Pulse.
    """
    logger.info(f"[ChatAPI] Mission stream started for {identity.user_id}")

    async def _mission_generator():
        try:
            # Engage the central LeviBrain (Sovereign OS Heart)
            async for event in await brain.route(
                user_id=identity.user_id,
                user_input=request.message,
                session_id=request.session_id,
                streaming=True,
                user_tier=identity.tier,
                mood=request.mood or "philosophical"
            ):
                # Unified SSE protocol for the v7 frontend (api.js compatibility)
                if "token" in event:
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': event['token']}}]})}\n\n"
                elif "event" in event:
                    if event["event"] == "activity":
                        yield f"data: {json.dumps({'type': 'activity', 'message': event['data']})}\n\n"
                    elif event["event"] == "metadata":
                        yield f"data: {json.dumps({'metadata': event['data']})}\n\n"
                    else:
                        # Fallback for other events
                        yield f"data: {json.dumps({'event': event['event'], 'data': event['data']})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"[ChatAPI] Mission failure: {e}")
            yield f"event: error\ndata: {json.dumps('Sovereign mission interrupted.')}\n\n"

    return StreamingResponse(_mission_generator(), media_type="text/event-stream")
