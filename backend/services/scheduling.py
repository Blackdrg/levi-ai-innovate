import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select, update
from backend.db.postgres_db import get_write_session, get_read_session
from backend.db.models import MissionSchedule
from backend.api.v8.orchestrator import brain # Re-use the brain core

logger = logging.getLogger(__name__)

async def schedule_mission(user_id: str, name: str, mission_input: str, interval_seconds: int):
    """
    Schedules a recurring mission for a user.
    Note: Standard v13.0 uses interval_seconds for simplicity.
    """
    next_run = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
    
    try:
        async with get_write_session() as session:
            new_schedule = MissionSchedule(
                user_id=user_id,
                name=name,
                mission_input=mission_input,
                interval_seconds=interval_seconds,
                next_run_at=next_run
            )
            session.add(new_schedule)
        return True
    except Exception as e:
        logger.error(f"[Scheduling] Failed to manifest mission schedule: {e}")
        return False

async def trigger_scheduled_missions():
    """
    The 'Sovereign Pulse' for scheduled tasks.
    Checks for missions that need to run and executes them.
    """
    now = datetime.now(timezone.utc)
    
    try:
        async with get_read_session() as session:
            query = select(MissionSchedule).where(
                MissionSchedule.is_active == True,
                MissionSchedule.next_run_at <= now
            )
            res = await session.execute(query)
            pending_missions = res.scalars().all()
            
        for mission in pending_missions:
            logger.info(f"[Scheduled Mission] Triggering: {mission.name} for {mission.user_id}")
            
            # Execute mission (v13 Monolith Sync loop for workers)
            # We use an async task to avoid blocking the scheduler loop
            import asyncio
            asyncio.create_task(run_one_scheduled_mission(mission))
            
    except Exception as e:
        logger.error(f"[Scheduling] Loop failure: {e}")

async def run_one_scheduled_mission(mission: MissionSchedule):
    """ Executes a single scheduled mission and updates its next run time. """
    try:
        # Step 1: Execution
        await brain.run_mission_sync(
            input_text=mission.mission_input,
            user_id=mission.user_id,
            session_id=f"scheduled_{mission.id}_{datetime.now().strftime('%Y%m%d%H%M')}"
        )
        
        # Step 2: Update next run time
        async with get_write_session() as session:
            new_next = datetime.now(timezone.utc) + timedelta(seconds=mission.interval_seconds)
            upd_query = update(MissionSchedule).where(MissionSchedule.id == mission.id).values(
                last_run_at=datetime.now(timezone.utc),
                next_run_at=new_next
            )
            await session.execute(upd_query)
        
        logger.info(f"[Scheduled Mission] {mission.name} completed and rescheduled.")
    except Exception as e:
        logger.error(f"[Scheduled Mission] Failure for {mission.name}: {e}")
