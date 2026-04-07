import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from backend.services.scheduling import schedule_mission
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduling", tags=["Scheduled Missions"])

@router.post("/create")
async def create_scheduled_mission(
    name: str,
    mission_input: str,
    interval_seconds: int = Query(3600, ge=60), # Minimum 1 minute
    current_user: dict = Depends(get_current_user)
):
    """
    Sovereign Scheduling: Recurring Mission Creation (v13.0.0).
    Schedules a mission for periodic autonomous execution.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    
    try:
        success = await schedule_mission(user_id, name, mission_input, interval_seconds)
        if success:
            return {"status": "success", "message": f"Mission '{name}' scheduled for pulse every {interval_seconds}s."}
        else:
            raise HTTPException(status_code=500, detail="Failed to sync scheduling pulse.")
    except Exception as e:
        logger.error(f"[Scheduling] API failure: {e}")
        raise HTTPException(status_code=500, detail="Neural drift in scheduling controller.")
