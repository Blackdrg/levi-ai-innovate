"""
Sovereign Telemetry API v13.0.0.
High-fidelity neural pulse streaming and identity trait retrieval.
"""

import logging
import json
import zlib
import base64
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Any, Dict
from datetime import datetime, timezone

from backend.broadcast_utils import SovereignBroadcaster
from backend.db.vector_store import VectorDB
from backend.utils.encryption import SovereignVault
from backend.api.utils.auth import get_current_user
from backend.core.workflow_contract import validate_workflow_integrity
from backend.core.task_graph import TaskGraph, TaskNode
from backend.core.orchestrator_types import ToolResult

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
            "status": "SOVEREIGN_OS_ONLINE",
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


@router.get("/swarm")
async def get_swarm_status():
    """
    Returns the real-time status of the Sovereign DCN Swarm.
    """
    from backend.db.redis import r_async
    
    if not r_async:
        return {"status": "offline", "nodes": []}

    try:
        raw_nodes = await r_async.hgetall("dcn:swarm:nodes")
        swarm_nodes = []
        
        now = datetime.now(timezone.utc).timestamp()
        
        for node_id, data_json in raw_nodes.items():
            try:
                node_data = json.loads(data_json)
                last_seen = node_data.get("last_seen", 0)
                
                # Mark as offline if no heartbeats for 90s
                is_online = (now - last_seen) < 90
                
                swarm_nodes.append({
                    "id": node_id,
                    "status": "online" if is_online else "offline",
                    "role": node_data.get("node_role", "unknown"),
                    "cpu": node_data.get("cpu_percent", 0),
                    "memory": node_data.get("memory_percent", 0),
                    "last_seen": datetime.fromtimestamp(last_seen, tz=timezone.utc).isoformat()
                })
            except Exception:
                continue

        return {
            "status": "active" if swarm_nodes else "standalone",
            "count": len(swarm_nodes),
            "nodes": swarm_nodes
        }
    except Exception as e:
        logger.error(f"[DCN] Swarm status retrieval failed: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/workflow")
async def get_pipeline_workflow(current_user: Any = Depends(get_current_user)):
    """
    Returns the designated end-to-end workflow manifest for operational inspection.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    sample_graph = TaskGraph(
        nodes=[
            TaskNode(
                id="t_core",
                agent="chat_agent",
                description="Primary reasoning pass",
                inputs={"input": "workflow probe"},
            )
        ]
    )
    workflow = validate_workflow_integrity(
        request_id=f"workflow_probe:{user_id}",
        perception={"intent": {"intent_type": "chat"}},
        goal=type("Goal", (), {"objective": "Serve response through designated workflow"})(),
        task_graph=sample_graph,
        results=[ToolResult(success=True, message="ok", agent="chat_agent", data={})],
        memory_event={"id": "probe", "checksum": "n/a", "version": 1},
    )
    return {
        "status": "connected",
        "workflow": workflow,
        "contracts": {
            "trace_headers": ["X-Trace-ID", "X-Sovereign-Version", "X-Cloud-Fallback"],
            "core_metrics": [
                "node_latency_ms",
                "dag_depth_distribution",
                "executor_queue_depth",
                "tool_budget_rejections_total",
                "alerts_total",
            ],
        },
    }
