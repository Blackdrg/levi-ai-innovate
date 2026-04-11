# backend/api/telemetry.py
import logging
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.auth import get_current_user
from backend.main import orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telemetry", tags=["Sovereign Telemetry"])

@router.get("/stream/{mission_id}")
async def stream_mission(mission_id: str, current_user = Depends(get_current_user)):
    """
    SSE stream for mission telemetry.
    Sovereign v14.2: Diverted to per-user channel with client-side filtering.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator offline")

    user_id = getattr(current_user, "id", "global")
    return StreamingResponse(
        orchestrator.stream_mission_events(user_id), 
        media_type="text/event-stream"
    )

@router.get("/pulse")
async def global_telemetry_stream(current_user = Depends(get_current_user)):
    """
    Global system-wide SSE stream for cognitive pulse.
    Includes VRAM pressure, DCN health, and active mission count.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator offline")

    async def event_generator():
        while True:
            pulse = {
                "type": "system_pulse",
                "timestamp": asyncio.get_event_loop().time(),
                "data": {
                    "vram_pressure": await orchestrator.check_vram_pressure(),
                    "active_missions": await orchestrator.count_active_missions(),
                    "dcn_health": await orchestrator.get_dcn_health()
                }
            }
            yield f"data: {json.dumps(pulse)}\n\n"
            await asyncio.sleep(2)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/workflow/{mission_id}")
async def get_workflow_trace(mission_id: str, current_user = Depends(get_current_user)):
    """
    Detailed workflow trace for a completed or in-flight mission.
    Returns the full DAG execution log.
    """
    trace = await orchestrator.get_mission_trace(mission_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Workflow trace not found.")
    return trace

def broadcast_mission_event(user_id: str, event_type: str, data: dict):
    """
    Sovereign v14.2: Telemetry Pulse Broadcaster.
    Emits events to Redis PubSub for SSE consumption.
    """
    from backend.broadcast_utils import SovereignBroadcaster
    SovereignBroadcaster.publish(event_type, data, user_id=user_id)

