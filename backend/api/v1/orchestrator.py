"""
Sovereign Orchestration Gateway v8.
Primary interface for the LEVI-AI OS Brain.
Bridges REST/SSE requests to the production-grade LeviBrainV8.
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.auth.models import UserProfile as UserIdentity
from backend.core.brain import LeviBrainV8
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestrator"])

# Initialize production LeviBrain instance
brain = LeviBrainV8()

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's query")
    session_id: Optional[str] = None
    mood: str = "philosophical"

# Dependency handled via backend.auth.logic.get_current_user

@router.post("/chat")
async def orchestrate_vision(
    request: ChatRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Standard AI mission (Blocking).
    Dispatches the vision to the Brain and awaits the final synthesis.
    """
    logger.info(f"[Gateway] Strategic mission started for {identity.user_id}")
    
    # Injection & PII protection at the edge
    if SovereignSecurity.detect_injection(request.message):
        raise HTTPException(status_code=400, detail="Neural protocol violation detected.")

    try:
        # We bridge to the production LeviBrain engine
        res = await brain.run(
            user_id=identity.get("uid") if isinstance(identity, dict) else identity.uid,
            user_input=request.message,
            session_id=request.session_id,
            mood=request.mood
        )
        
        return {
            "response": res.get("response", ""),
            "intent": res.get("intent", "chat"),
            "session_id": request.session_id or str(asyncio.get_event_loop().time()),
            "status": "success",
            "metadata": res.get("decision", {})
        }
    except Exception as e:
        logger.error(f"[Gateway] Orchestration failure: {e}")
        return {"status": "error", "message": "The cosmic brain encountered an anomaly."}

@router.post("/chat/stream")
async def orchestrate_stream(
    request: ChatRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Streaming AI mission (SSE).
    Real-time neural synthesis with activity pulses.
    """
    logger.info(f"[Gateway] Streaming mission started for {identity.user_id}")

    async def _brain_stream():
        # 1. Identity Pulse
        yield f"event: activity\ndata: {json.dumps('Sovereign Orchestration Active')}\n\n"
        
        try:
            # 2. Engage the production LeviBrain mission stream
            async for chunk in await brain.stream(
                user_id=identity.get("uid") if isinstance(identity, dict) else identity.uid,
                user_input=request.message,
                session_id=request.session_id,
                mood=request.mood
            ):
                # Standardized v7 SSE Protocol
                if "token" in chunk:
                    yield f"event: choice\ndata: {json.dumps(chunk['token'])}\n\n"
                elif "event" in chunk:
                    yield f"event: {chunk['event']}\ndata: {json.dumps(chunk['data'])}\n\n"
            
            # 3. Finalization pulse
            yield f"event: done\ndata: {json.dumps('[MISSION_COMPLETE]')}\n\n"
            
        except Exception as e:
            logger.error(f"[Gateway] Streaming failure: {e}")
            yield f"event: error\ndata: {json.dumps('Cosmic synchronization failed.')}\n\n"

    return StreamingResponse(_brain_stream(), media_type="text/event-stream")
