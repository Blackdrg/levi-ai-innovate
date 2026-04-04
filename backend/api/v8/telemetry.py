"""
Sovereign Telemetry API v13.0.0.
High-fidelity neural pulse streaming and identity trait retrieval.
"""

import logging
import asyncio
import json
import zlib
import base64
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.broadcast_utils import SovereignBroadcaster
from backend.db.vector_store import VectorDB
from backend.utils.encryption import SovereignVault
from backend.api.utils.auth import get_current_user

router = APIRouter(prefix="", tags=["Telemetry v13"])
logger = logging.getLogger(__name__)

def broadcast_mission_event(user_id: str, event_type: str, data: Dict[str, Any]):
    """
    Unified v13 Mission Pulse Bridge with Structured Audit Logging.
    """
    audit_payload = {
        "user_id": user_id,
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": data
    }
    logger.info(f"[AUDIT-v13] Mission Pulse: {json.dumps(audit_payload)}")
    
    # SSE Broadcast
    SovereignBroadcaster.publish(event_type, data, user_id=user_id)


@router.get("/stream")
async def stream_telemetry(
    request: Request, 
    profile: str = "desktop",
    current_user: Any = Depends(get_current_user)
):
    """
    SSE endpoint to stream real-time mission telemetry (v13.0 Pulse).
    Supports 'Adaptive Pulse v4.1' (Binary/zlib) for mobile profiles.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Telemetry-v13] Link established for {user_id} (Profile: {profile})")
    
    async def pulse_generator():
        # v13.0.0 Protocol Handshake
        handshake = {
            "version": "13.0.0",
            "status": "SOVEREIGN_ABS_MONOLITH_ONLINE",
            "profile": profile
        }
        yield f"event: pulse_handshake\ndata: {json.dumps(handshake)}\n\n"

        async for chunk in SovereignBroadcaster.subscribe(user_id=user_id, profile=profile):
            event = chunk.get("event", "message")
            data_raw = chunk.get("data", {})
            
            # v4.1 Adaptive Compression (Mobile Only)
            if profile == "mobile":
                json_str = json.dumps(data_raw)
                compressed = zlib.compress(json_str.encode())
                encoded = base64.b64encode(compressed).decode()
                yield f"event: {event}\ndata: {encoded}\n\n"
            else:
                yield f"event: {event}\ndata: {json.dumps(data_raw)}\n\n"

    return StreamingResponse(pulse_generator(), media_type="text/event-stream")


@router.get("/crystallized-traits")
async def get_crystallized_traits(current_user: Any = Depends(get_current_user)):
    """
    Returns the user's crystallized identity traits (v13.0 SQL Mirror).
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    
    # 1. HNSW Vector Recall
    traits_db = await VectorDB.get_user_collection(user_id, "traits")
    results = await traits_db.search("trait", limit=50, min_score=0.1)
    
    decrypted_traits = []
    for res in results:
        try:
            plain_text = SovereignVault.decrypt(res.get("text", ""))
            decrypted_traits.append({
                "trait": plain_text,
                "crystallized_at": res.get("crystallized_at", datetime.now().isoformat())
            })
        except Exception:
            pass
        
    return {"traits": decrypted_traits, "status": "pulsing_v13"}
