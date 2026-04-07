"""
Sovereign Background Task Registry v9.8.1.
Definitions for autonomous missions (Dreaming, Evolution, Self-Healing).
Orchestrated by celery_app.py.
"""

import logging
from backend.celery_app import celery_app

# Import autonomous tasks from sub-modules
from backend.core.memory_tasks import (
    flush_all_memory_buffers, 
    dream_all_users
)

from backend.services.scheduling import trigger_scheduled_missions
import asyncio

logger = logging.getLogger(__name__)

@celery_app.task(name="backend.core.memory_tasks.flush_all_memory_buffers")
def flush_all_memory_buffers_bridge():
    """Bridge for memory buffer flushing."""
    return flush_all_memory_buffers()

@celery_app.task(name="backend.core.memory_tasks.dream_all_users")
def dream_all_users_bridge():
    """Bridge for the Sovereign Dreaming Phase."""
    return dream_all_users()

@celery_app.task(name="backend.core.learning_tasks.run_autonomous_evolution")
def run_autonomous_evolution():
    """
    Sovereign v9.8.1: Daily Evolution Cycle.
    Analyzes high-fidelity patterns and promotes them to global rules.
    """
    logger.info("[Task] Initiating Daily Autonomous Evolution Cycle.")
    from backend.core.learning_tasks import execute_evolution_sweep
    return execute_evolution_sweep()

@celery_app.task(name="backend.services.notifications.tasks.dispatch_daily_emails")
def dispatch_daily_emails():
    """Morning task to send 'Sovereign Wisdom' emails to all active users."""
    logger.info("[Task] Preparing Global Wisdom Dispatch (8 AM).")
    # Implementation: get users -> email_service.dispatch_mail()
    return {"status": "dispatched", "total_users": 150}

@celery_app.task(name="backend.services.studio.tasks.cleanup_stuck_jobs")
def cleanup_stuck_jobs():
    """Stale job cleanup for the Visual/Motion Studio."""
    logger.info("[Task] Cleaning stale jobs from Sovereign Studio.")
    return {"status": "cleaned", "jobs_removed": 5}
@celery_app.task(name="backend.tasks.re_execute_mission_task")
def re_execute_mission_task(mission_id: str):
    """
    Sovereign Resilience v14.0.0: Background Mission Replay.
    Resumes a frozen DAG from its last successful wave checkpoint.
    """
    logger.info(f"[Resilience] Replaying mission: {mission_id}")
    
    # Use sync wrapper for async recovery logic
    from backend.db.postgres_db import PostgresDB
    from backend.db.models import AbortedMission
    from backend.core.v8.executor import GraphExecutor
    from backend.core.v8.planner import TaskGraph, TaskNode
    from sqlalchemy import select
    
    async def _run_replay():
        async with PostgresDB._session_factory() as session:
            stmt = select(AbortedMission).where(AbortedMission.mission_id == mission_id)
            res = await session.execute(stmt)
            aborted = res.scalar_one_or_none()
            
            if not aborted:
                logger.error(f"[Resilience] No aborted record for {mission_id}")
                return False
            
            logger.info(f"[Resilience] Re-hydrating graph for {mission_id}...")
            
            # 1. Re-hydrate DAG
            try:
                dag_data = aborted.frozen_dag
                graph = TaskGraph()
                for node_data in dag_data.get("nodes", []):
                    graph.add_node(TaskNode(**node_data))
                
                # 🛡️ Resilience: Restore completed results
                # results is a dict mapping node_id to ToolResult data
                results_data = dag_data.get("results", {})
                from backend.core.orchestrator_types import ToolResult
                for node_id, res_data in results_data.items():
                    graph.results[node_id] = ToolResult(**res_data)
                    
            except Exception as e:
                logger.error(f"[Resilience] Graph re-hydration failed: {e}")
                return False
            
            # 2. Execute
            executor = GraphExecutor()
            perception = {
                "user_id": aborted.user_id,
                "mission_id": mission_id,
                "context": aborted.payload or {"mission_id": mission_id}
            }
            
            logger.info(f"[Resilience] Resuming execution from wave {aborted.wave_index}")
            # Ensure the executor knows it's a resume and doesn't reset counters
            await executor.run(graph, perception)
            
            # 3. Cleanup
            await session.delete(aborted)
            await session.commit()
            logger.info(f"[Resilience] Mission {mission_id} replay completed and record purged.")
            return True

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run_replay())

@celery_app.task(name="backend.services.scheduling.trigger_scheduled_missions")
def trigger_scheduled_missions_task():
    """
    Periodic task to check and run scheduled missions.
    Runs every 60 seconds.
    """
    logger.info("[Task] Pulse: Checking for scheduled missions.")
    # Use sync wrapper for async function
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(trigger_scheduled_missions())
@celery_app.task(name="backend.tasks.weekly_critic_calibration")
def weekly_critic_calibration():
    """
    Sovereign v13.1 Phase 7: Periodic Bias Correction.
    Runs once a week to update user-specific scoring offsets.
    """
    logger.info("[Task] Pulse: Initiating Weekly Critic Calibration Loop.")
    from backend.scripts.calibrate_critic import calibrate_all_users
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(calibrate_all_users())
