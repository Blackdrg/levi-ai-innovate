# backend/api/telemetry.py
import logging
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from backend.auth import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Sovereign Telemetry"])

@router.get("/stream/{mission_id}")
async def stream_mission(mission_id: str, current_user = Depends(get_current_user)):
    """
    SSE stream for mission telemetry.
    Sovereign v14.2: Diverted to per-user channel with client-side filtering.
    """
    from backend.main import orchestrator
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
    from backend.main import orchestrator
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
    
    async def listen_and_send(user_id: str):
        try:
            async for pulse in SovereignBroadcaster.subscribe(user_id):
                # SovereignBroadcaster.subscribe yields SSE-formatted strings
                # We need to extract the JSON data part for the WebSocket
                # Each pulse is like "event: type\ndata: {...}\n\n"
                lines = pulse.split("\n")
                data_line = next((l for l in lines if l.startswith("data: ")), None)
                if data_line:
                    data_str = data_line[6:]
                    try:
                        await websocket.send_text(data_str)
                    except Exception:
                        break
        except Exception as e:
            logger.error(f"[Telemetry] WS Broadcaster task failed: {e}")

    # Start subscription tasks
    tasks = [
        asyncio.create_task(listen_and_send(f"user:{client_id}")),
        asyncio.create_task(listen_and_send("system:pulse")),
        asyncio.create_task(listen_and_send("global"))
    ]
    
    try:
        while True:
            # Check for client disconnect
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
                
    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info(f"[Telemetry] WebSocket client {client_id} disconnected.")
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

@router.websocket("/ws/telemetry")
async def telemetry_websocket_kernel(websocket: WebSocket):
    """
    Dedicated WebSocket for Real-Time Kernel Telemetry.
    Streams structured records from the serial bridge.
    """
    await websocket.accept()
    from backend.broadcast_utils import SovereignBroadcaster
    
    try:
        async for pulse in SovereignBroadcaster.subscribe("system:pulse"):
            # Each pulse looks like "event: kernel_event\ndata: {...}\n\n"
            lines = pulse.split("\n")
            data_line = next((l for l in lines if l.startswith("data: ")), None)
            if data_line:
                data_str = data_line[6:]
                await websocket.send_text(data_str)
    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info("[Telemetry] Kernel WebSocket disconnected.")
    except Exception as e:
        logger.error(f"[Telemetry] Kernel WS failed: {e}")

@router.get("/workflow/{mission_id}")
async def get_workflow_trace(mission_id: str, current_user = Depends(get_current_user)):
    """
    Detailed workflow trace for a completed or in-flight mission.
    Returns the full DAG execution log.
    """
    from backend.main import orchestrator
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

