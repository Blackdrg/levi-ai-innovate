"""
Sovereign Chat API v13.0.0.
High-fidelity conversational interface for the LEVI-AI OS.
Bridges to the LeviBrainCoreController and SovereignGenerator (v13.0.0).
Hardened for Adaptive Pulse v4.1 (Binary/zlib) and identity-aware context.
"""

import logging
import json
import zlib
import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.core.orchestrator import orchestrator as brain
from backend.engines.utils.security import SovereignSecurity

# Production v14.1 Brain Singleton

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat"])

class ChatMessage(BaseModel):
    message: str
    session_id: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

@router.post("")
async def conversational_endpoint_v13(
    request: ChatMessage,
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Sovereign Mission (v13.0.0 Monolith) - Synchronous.
    """
    uid = getattr(identity, "uid", "guest")
    logger.info(f"[ChatAPI-v13] Mission Initiated: {uid}")
    
    if SovereignSecurity.detect_injection(request.message):
        raise HTTPException(status_code=400, detail="Neural protocol violation.")

    try:
        res = await brain.run(
            user_input=request.message,
            user_id=uid,
            session_id=request.session_id,
            mood="philosophical"
        )
        
        return {
            "response": res.get("response", ""),
            "session_id": request.session_id,
            "engine": "sovereign_os_v14.0.0",
            "status": "success",
            "metadata": {
                "decision": res.get("decision"),
                "resonance": res.get("resonance", 1.0),
                "fidelity": res.get("fidelity_score", 1.0)
            }
        }
    except Exception as e:
        logger.error(f"[ChatAPI-v13] Mission Failure: {e}")
        return {"status": "error", "message": "The Sovereign OS encountered an anomaly."}

@router.post("/stream")
async def conversational_stream_endpoint_v13(
    request: ChatMessage,
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Sovereign Mission Stream (v13.0.0) - Adaptive Pulse v4.1 (Binary/zlib).
    """
    uid = getattr(identity, "uid", "guest")
    logger.info(f"[ChatAPI-v13] Mission Stream Initiated: {uid}")

    async def _mission_generator():
        try:
            async for event in brain.stream(
                user_input=request.message,
                user_id=uid,
                session_id=request.session_id,
                mood="philosophical"
            ):
                # Adaptive Pulse v4.1: Binary Encoding
                event_type = event.get("event", "data")
                data = event.get("data", event)
                
                if event_type == "pulse":
                    json_data = json.dumps(data).encode('utf-8')
                    compressed = zlib.compress(json_data)
                    encoded = base64.b64encode(compressed).decode('utf-8')
                    yield f"event: pulse_v4\ndata: {encoded}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[ChatAPI-v13] Stream Failure: {e}")
            yield f"event: error\ndata: {json.dumps(('Sovereign OS synchronization failed.'))}\n\n"

    return StreamingResponse(_mission_generator(), media_type="text/event-stream")
