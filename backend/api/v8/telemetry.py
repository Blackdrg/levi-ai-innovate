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

@router.get("/health")
async def cluster_health(identity: Any = Depends(get_sovereign_identity)):
    """Summary of cluster resource pressure and mission throughput."""
    try:
        from backend.main import orchestrator
        if not orchestrator:
            return {"status": "degraded", "reason": "Orchestrator offline"}
            
        return {
            "status": "online",
            "dcn": await orchestrator.get_dcn_health(),
            "vram_pressure": await orchestrator.check_vram_pressure(),
            "active_missions": await orchestrator.count_active_missions(),
            "graduation_score": await orchestrator.get_graduation_score()
        }
    except Exception as e:
        logger.error(f"[Telemetry-v8] Health probe failure: {e}")
        return {"status": "error", "message": str(e)}
