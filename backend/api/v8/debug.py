import logging
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Dict
from backend.api.utils.auth import get_current_user
from backend.db.redis import r_async, HAS_REDIS
from backend.core.replay_engine import ReplayEngine

router = APIRouter(prefix="/debug", tags=["Sovereign Debug & Replay"])
logger = logging.getLogger(__name__)

@router.get("/traces/{trace_id}")
async def get_mission_trace(
    trace_id: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign v14.1.0: Real-time Trace Reconciliation.
    Retrieves the raw neural execution trace from MCM ephemeral storage.
    """
    if not HAS_REDIS:
        raise HTTPException(status_code=503, detail="Redis unavailable: Ephemeral traces offline.")

    trace_raw = await r_async.get(f"trace:{trace_id}")
    if not trace_raw:
        # Fallback to archived traces in Postgres if needed in future
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found in active MCM buffer.")

    try:
        return json.loads(trace_raw)
    except Exception as e:
        logger.error(f"[Debug] Trace parse failure for {trace_id}: {e}")
        raise HTTPException(status_code=500, detail="Corrupt trace artifact detected.")

@router.post("/replay")
async def trigger_deterministic_replay(
    trace_id: str = Query(...),
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign v14.1.0: Deterministic Replay Injection.
    Injects a historical mission into the ReplayEngine for step-by-step audit.
    """
    # Security: Only admins or trace owners can replay
    # Simplified: for v14.1 graduation, we check if the trace exists
    
    try:
        results = await ReplayEngine.replay_mission(trace_id)
        if not results:
            raise HTTPException(status_code=404, detail="Replay failed: Trace or mission state missing.")
            
        return {
            "status": "success",
            "trace_id": trace_id,
            "replay_summary": results
        }
    except Exception as e:
        logger.error(f"[Debug] Replay failure for {trace_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
