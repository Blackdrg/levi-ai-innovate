"""
Sovereign Telemetry Engine v8.0.0.
High-fidelity SSE stream for cognitive pulses and swarm monitoring.
"""

import logging
import json
import asyncio
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Any, Optional

from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Swarm Telemetry"])

@router.get("/stream")
async def stream_telemetry_v8(
    user_id: Optional[str] = Query(None, description="Optional filter for specific consciousness ID"),
    identity: Any = Depends(get_sovereign_identity)
):
    """
    Sovereign Swarm Telemetry Stream (v8.0.0).
    Aggregates neural pulses, mission transitions, and cluster resource pressure.
    """
    authorized_uid = getattr(identity, "uid", "guest")
    target_uid = user_id or authorized_uid 
    
    logger.info(f"[Telemetry-v8] Pulse stream opened for {authorized_uid} (Tracing: {target_uid})")

    async def _telemetry_generator():
        try:
            # Subscribe to global cognitive broadcasts
            async for pulse in SovereignBroadcaster.subscribe(target_uid):
                yield f"event: pulse\ndata: {json.dumps(pulse)}\n\n"
        except asyncio.CancelledError:
            logger.info(f"[Telemetry-v8] Stream closed for {authorized_uid}")
        except Exception as e:
            logger.error(f"[Telemetry-v8] Stream anomaly: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(_telemetry_generator(), media_type="text/event-stream")

@router.get("/kernel")
async def kernel_state(identity: Any = Depends(get_sovereign_identity)):
    """Summary of the Rust Kernel (Cognitive + Microkernel) health and throughput."""
    try:
        from backend.kernel.kernel_wrapper import kernel
        if not kernel.rust_kernel:
            return {"status": "fallback", "reason": "Rust binary not loaded. Using Python fallback."}
            
        return {
            "status": "online",
            "vram_quota": 8000.0,
            "vram_used": await asyncio.to_thread(lambda: kernel.rust_kernel.vram_used), # Assuming property access
            "active_agents": await asyncio.to_thread(lambda: len(kernel.rust_kernel.agents)),
            "message_backlog": 0,
            "latency": "sub-ms"
        }
    except Exception as e:
        logger.error(f"[Telemetry-v8] Kernel state probe failure: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/metrics")
async def get_json_metrics(identity: Any = Depends(get_sovereign_identity)):
    """Exposes real-time system metrics as JSON for the Sovereign Evolution Dashboard."""
    try:
        from backend.utils.metrics import MetricsHub
        # In a real environment, we'd pull from MetricsHub or state registry
        # Here we bridge to the underlying metrics collectors
        from backend.core.v13.vram_guard import VRAMGuard
        vram_guard = VRAMGuard()
        device_slots = await vram_guard.get_device_slots()
        
        vram_total = sum(d["vram_total_mb"] for d in device_slots)
        vram_used = sum(d["vram_used_mb"] for d in device_slots)
        vram_percent = (vram_used / vram_total * 100) if vram_total > 0 else 0
        
        from backend.utils.circuit_breaker import circuit_breaker
        from backend.utils.metrics import ACTIVE_MISSIONS, AGENT_LATENCY
        
        return {
            "status": "online",
            "vram_usage_percent": round(vram_percent, 1),
            "slots_active": sum(1 for d in device_slots if d["vram_used_mb"] > (d["vram_total_mb"] * 0.1)),
            "circuit_open": circuit_breaker.is_open(),
            "avg_latency": AGENT_LATENCY.get_sample_value("agent_latency_ms_sum") / (AGENT_LATENCY.get_sample_value("agent_latency_ms_count") or 1),
            "active_missions": int(ACTIVE_MISSIONS._value.get()),
            "ts": json.dumps(json.dumps("")) # Just for structure
        }
    except Exception as e:
        logger.error(f"[Telemetry-v8] JSON metrics failure: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/health")
async def cluster_health(identity: Any = Depends(get_sovereign_identity)):
    """Summary of cluster resource pressure and mission throughput."""
    try:
        # Avoid circular import with Orchestrator if possible, use singleton
        from backend.core.dcn_protocol import get_dcn_protocol
        from backend.utils.metrics import GRADUATION_SCORE, ACTIVE_MISSIONS
        
        dcn = get_dcn_protocol()
        mesh_health = await dcn.get_mesh_health()
            
        return {
            "status": "online",
            "dcn": mesh_health,
            "vram_pressure": 0.45, # Placeholder (calculated from VRAMGuard)
            "active_missions": int(ACTIVE_MISSIONS._value.get()),
            "graduation_score": GRADUATION_SCORE._value.get()
        }
    except Exception as e:
        logger.error(f"[Telemetry-v8] Health probe failure: {e}")
        return {"status": "error", "message": str(e)}

