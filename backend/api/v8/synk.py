"""
LEVI-AI Neural Synk API v13.0.
High-performance binary streaming for total visual sovereignty.
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v8/synk", tags=["Neural Synk"])

@router.get("/pulse/{user_id}")
async def neural_synk_pulse(user_id: str, request: Request, profile: str = "mobile"):
    """
    Sovereign v13.0: High-Fidelity Binary SSE Pulse.
    Bridges the real-time Broadcaster to the Synk endpoint.
    """
    from backend.broadcast_utils import SovereignBroadcaster
    logger.info(f"[Synk] Neural Synchrony Pulse linked for user: {user_id}")
    
    return StreamingResponse(
        SovereignBroadcaster.subscribe(user_id=user_id, profile=profile),
        media_type="text/event-stream"
    )

@router.post("/broadcast")
async def broadcast_to_network(payload: dict):
    """
    Broadcasts intelligence fragments to the DCN via Synk.
    Verifies the HMAC signature before merging foreign rules into the local brain.
    """
    from backend.core.v8.sync_engine import SovereignSync
    
    logger.info("[Synk] Decoding intelligence fragment from DCN...")
    
    count = await SovereignSync.import_external_rules(payload)
    if count > 0:
        return {"status": "success", "imported": count, "message": f"Neural Synk: {count} brain fragments merged."}
    else:
        return {"status": "denied", "imported": 0, "message": "Signatory rejection or empty payload."}

@router.post("/push")
async def push_local_rules():
    """Triggers a manual sync of local crystallized rules to the DCN Collective Hub."""
    from backend.core.v8.sync_engine import SovereignSync
    logger.info("[Synk] Initiating manual DCN push...")
    await SovereignSync.sync_with_collective_hub()
    return {"status": "dispatched", "target": "DCN_COLLECTIVE_HUB"}
