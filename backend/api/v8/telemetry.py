import logging
import asyncio
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.broadcast_utils import SovereignBroadcaster
from backend.db.vector_store import VectorDB
from backend.utils.encryption import SovereignVault
from backend.api.utils.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

def broadcast_mission_event(user_id: str, event_type: str, data: Dict[str, Any]):
    """
    Unified V8 Mission Pulse Bridge with Structured Audit Logging.
    Communicates execution state to the frontend and logs to the system audit trail.
    """
    # 1. Structured Audit Log (Production Requirement)
    audit_payload = {
        "user_id": user_id,
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": data
    }
    logger.info(f"[AUDIT] Mission Event: {json.dumps(audit_payload)}")
    
    # 2. Real-Time Broadcast (SSE)
    SovereignBroadcaster.publish(event_type, data, user_id=user_id)


# --- Unified v8 Pulse Stream ---


@router.get("/stream")
async def stream_telemetry(
    request: Request, 
    profile: str = "desktop",
    current_user: Any = Depends(get_current_user)
):
    """
    SSE endpoint to stream real-time mission telemetry (Redis Pulse).
    Supports 'profile' parameter for adaptive filtering and compression.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Telemetry] User {user_id} connected to v8 Pulse stream. Profile: {profile}")
    
    return StreamingResponse(
        SovereignBroadcaster.subscribe(user_id=user_id, profile=profile), 
        media_type="text/event-stream"
    )


@router.get("/crystallized-traits")
async def get_crystallized_traits(current_user: Any = Depends(get_current_user)):
    """
    Returns the user's crystallized identity traits (Decrypted).
    User Requirement: High-fidelity identity-level encryption at rest.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    
    traits_db = await VectorDB.get_user_collection(user_id, "traits")
    # Search for all traits (empty query or generic)
    results = await traits_db.search("trait", limit=50, min_score=0.1)
    
    decrypted_traits = []
    for res in results:
        # Decrypt for the authorized user
        plain_text = SovereignVault.decrypt(res.get("text", ""))
        decrypted_traits.append({
            "trait": plain_text,
            "crystallized_at": res.get("crystallized_at")
        })
        
    return {"traits": decrypted_traits}
