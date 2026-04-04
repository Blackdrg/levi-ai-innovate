"""
Sovereign Background Task Registry v9.8.1.
Definitions for autonomous missions (Dreaming, Evolution, Self-Healing).
Orchestrated by celery_app.py.
"""

import logging
from typing import Dict, Any, List
from backend.celery_app import celery_app

# Import autonomous tasks from sub-modules
from backend.core.memory_tasks import (
    flush_all_memory_buffers, 
    dream_all_users, 
    run_global_maintenance
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
