# backend/api/telemetry.py
import logging
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
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
    
@router.websocket("/ws/{client_id}")
async def telemetry_websocket(websocket: WebSocket, client_id: str):
    """
    Sovereign v15.0: Bi-Directional Telemetry WebSocket.
    Provides sub-100ms updates on cognitive ops.
    """
    await websocket.accept()
    from backend.broadcast_utils import SovereignBroadcaster
    
    # Subscribe to global and client-specific channels
    queue = asyncio.Queue()
    
    def on_event(event_data):
        asyncio.create_task(queue.put(event_data))

    subscription = SovereignBroadcaster.subscribe(f"user:{client_id}", on_event)
    global_sub = SovereignBroadcaster.subscribe("system:pulse", on_event)
    
    try:
        while True:
            # Check for incoming messages (e.g. commands to pause/resume)
            try:
                # Non-blocking check for internal queue
                event = await asyncio.wait_for(queue.get(), timeout=0.1)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                pass
            
            # Check for client disconnect
            try:
                # We don't expect much from client, but we must pump the receiver
                await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
                
    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info(f"[Telemetry] WebSocket client {client_id} disconnected.")
    finally:
        SovereignBroadcaster.unsubscribe(subscription)
        SovereignBroadcaster.unsubscribe(global_sub)

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

