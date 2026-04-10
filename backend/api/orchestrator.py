"""
Sovereign Orchestration Gateway v7.
Primary interface for the LEVI-AI OS Brain.
Bridges REST/SSE requests to the production-grade BrainOrchestrator.
"""

import logging
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth import SovereignAuth, UserIdentity
from backend.core.orchestrator import orchestrator as brain

async def handle_chat(user_input, user_id, session_id=None, tier='free'):
    """v14.0: Unified cognitive execution pass."""
    result = await brain.run(
        user_input=user_input, 
        user_id=user_id,
        session_id=session_id
    )
    return result

async def stream_chat(user_input, user_id, session_id=None, tier='free'):
    """v14.0: Token-by-token cognitive streaming."""
    yield {"type": "activity", "data": "Synchronizing Sovereignty..."}
    
    async for chunk in brain.stream(
        user_id=user_id,
        user_input=user_input,
        session_id=session_id
    ):
        if "token" in chunk:
            yield {"type": "token", "data": chunk["token"]}
        elif "event" in chunk:
            yield {"type": "activity", "data": chunk.get("data") or f"Mission Pulse: {chunk['event']}"}


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's query")
    session_id: Optional[str] = None
    mood: str = "philosophical"

async def get_sovereign_identity(request: Request) -> UserIdentity:
    """Dependency to extract and verify the Sovereign Identity pulse."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # Default to guest identity for open-access endpoints
        return UserIdentity(user_id=f"guest_{request.client.host if request.client else 'local'}")
    
    token = auth_header.split(" ")[1]
    identity = SovereignAuth.verify_token(token)
    if not identity:
        raise HTTPException(status_code=401, detail="Sovereign Identity verification failed.")
    return identity

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
        # We bridge to the production LeviBrain engine (v14.0)
        res = await brain.run(
            user_id=identity.user_id,
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
            # 2. Engage the production LeviBrain mission stream (v14.0)
            async for chunk in brain.stream(
                user_id=identity.user_id,
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
