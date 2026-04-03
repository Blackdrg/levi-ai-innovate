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

from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.api.orchestrator import handle_chat, stream_chat


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
        # Bridged to the v8 Unified Orchestrator pass
        res = await handle_chat(
            user_input=request.message,
            user_id=identity.uid or identity.user_id
        )
        
        return {
            "response": res.get("response", ""),
            "session_id": request.session_id,
            "engine": "sovereign_brain_v8",
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
            # Engage the central stream via the v8 Orchestrator bridge
            async for event in stream_chat(
                user_input=request.message,
                user_id=identity.uid or identity.user_id
            ):
                # Standardized v8 SSE format
                if "type" in event:
                    if event["type"] == "token":
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': event['data']}}]})}\n\n"
                    elif event["type"] == "activity":
                        yield f"data: {json.dumps({'type': 'activity', 'message': event['data']})}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[ChatAPI] Stream failure: {e}")
            yield f"event: error\ndata: {json.dumps('Sovereign mission interrupted.')}\n\n"

    return StreamingResponse(_mission_generator(), media_type="text/event-stream")
