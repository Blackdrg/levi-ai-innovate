"""
Sovereign Resilience API v14.0.0.
Handles mission replay and recovery from wave checkpoints.
"""

import logging
from fastapi import APIRouter, HTTPException
from backend.tasks import re_execute_mission_task

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/{mission_id}/replay")
async def replay_mission(mission_id: str):
    """
    Restart an aborted mission from its last successful wave checkpoint.
    Dispatches a Celery task for reliable, isolated background execution.
    """
    try:
        # Enqueue for background execution (Celery)
        re_execute_mission_task.delay(mission_id)
        
        return {
            "status": "REPLAY_QUEUED",
            "mission_id": mission_id,
            "worker": "celery"
        }
    except Exception as e:
        logger.error(f"[Resilience] Failed to queue replay for {mission_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue mission replay.")
