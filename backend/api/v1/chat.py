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
from backend.core.v8.brain import LeviBrainCoreController
from backend.engines.utils.security import SovereignSecurity

# Global v9.8.1 Brain Singleton for Unified Missions
brain_v8 = LeviBrainCoreController()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat"])

@router.post("")
async def conversational_endpoint(
    request: ChatMessage,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Standard Sovereign Mission (Blocking) - Redirected to v9.8.1 Monolith.
    """
    logger.info(f"[ChatAPI v1] Mission redirected to v9.8.1 for {identity.user_id}")
    
    if SovereignSecurity.detect_injection(request.message):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        # Standardize on v9.8.1 Monolith Logic
        res = await brain_v8.run(
            user_input=request.message,
            user_id=identity.uid or identity.user_id,
            session_id=request.session_id
        )
        
        return {
            "response": res.get("response", ""),
            "session_id": request.session_id,
            "engine": "sovereign_monolith_v9.8.1",
            "status": "success",
            "metadata": {
                "decision": res.get("decision"),
                "resonance": res.get("resonance", 1.0)
            }
        }
    except Exception as e:
        logger.error(f"[ChatAPI v1] Mission failure: {e}")
        return {"status": "error", "message": "The monolith encountered an anomaly."}

@router.post("/stream")
async def conversational_stream_endpoint(
    request: ChatMessage,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Sovereign Mission Stream (SSE) - Redirected to v9.8.1 Monolith.
    """
    logger.info(f"[ChatAPI v1] Mission stream redirected to v9.8.1 for {identity.user_id}")

    async def _mission_generator():
        try:
            # v9.8.1: Unified Routing for tokens and events
            async for chunk in await brain_v8.route(
                user_input=request.message,
                user_id=identity.uid or identity.user_id,
                session_id=request.session_id,
                streaming=True
            ):
                if "token" in chunk:
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk['token']}}]})}\n\n"
                elif "event" in chunk:
                    yield f"data: {json.dumps({'type': 'pulse', 'event': chunk['event'], 'data': chunk.get('data')})}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[ChatAPI v1] Stream failure: {e}")
            yield f"event: error\ndata: {json.dumps('Monolith synchronization failed.')}\n\n"

    return StreamingResponse(_mission_generator(), media_type="text/event-stream")
