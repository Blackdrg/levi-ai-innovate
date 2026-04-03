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

from backend.api.orchestrator import handle_chat, stream_chat, brain
from backend.engines.utils.security import SovereignSecurity


logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Orchestrator V8"])

# Using the centralized brain instance from the v8 orchestrator


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's query")
    session_id: Optional[str] = None
    mood: str = "philosophical"

@router.post("/chat")
async def orchestrate_vision(
    request: ChatRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Standard AI mission (v8 Blocking).
    Dispatches the vision to the finalized v8 brain.
    """
    logger.info(f"[Gateway-V8] Mission started for {identity.user_id}")
    
    if SovereignSecurity.detect_injection(request.message):
        raise HTTPException(status_code=400, detail="Neural protocol violation detected.")

    try:
        # Unified v8 Cognitive Mission
        res = await handle_chat(
            user_input=request.message,
            user_id=identity.uid if hasattr(identity, "uid") else identity.user_id
        )
        
        # Strategic insight (merged from v1/brain.py logic)
        return {
            "response": res.get("response", ""),
            "intent": res.get("intent", "chat"),
            "strategy": res.get("intent", "chat"), # For compatibility with brain.py
            "confidence": res.get("audit", {}).get("total_score", 0.9),
            "session_id": request.session_id,
            "status": "success",
            "audit": res.get("audit", {}),
            "graph": res.get("graph", [])
        }
    except Exception as e:
        logger.error(f"[Gateway-V8] Orchestration failure: {e}")
        return {"status": "error", "message": "The finalized v8 brain encountered a cognitive resonance failure."}

@router.post("/chat/stream")
async def orchestrate_stream(
    request: ChatRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Streaming AI mission (v8 SSE).
    Real-time neural synthesis with multi-event pulses.
    """
    logger.info(f"[Gateway-V8] Stream mission started for {identity.user_id}")

    async def _brain_stream():
        try:
            # Engage the v8 unified cognitive stream
            async for event in stream_chat(
                user_input=request.message,
                user_id=identity.uid if hasattr(identity, "uid") else identity.user_id
            ):
                # Standardized v8.3 SSE Protocol
                if event["type"] == "token":
                    yield f"event: choice\ndata: {json.dumps(event['data'])}\n\n"
                elif event["type"] == "activity":
                    yield f"event: activity\ndata: {json.dumps(event['data'])}\n\n"
            
            yield f"event: done\ndata: {json.dumps('[MISSION_COMPLETE]')}\n\n"
        except Exception as e:
            logger.error(f"[Gateway-V8] Stream failure: {e}")
            yield f"event: error\ndata: {json.dumps('Cosmic synchronization failed (v8).')}\n\n"

    return StreamingResponse(_brain_stream(), media_type="text/event-stream")
