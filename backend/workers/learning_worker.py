"""
Sovereign Learning Workers v13.0.0.
Background orchestration for cognitive hygiene and self-evolution.
Synchronized with the Sovereign OS SQL Fabric.
"""

import logging
import asyncio
from backend.celery_app import celery_app
from backend.pipelines.learning import learning_system
from backend.services.learning.hygiene import SurvivalGater

logger = logging.getLogger(__name__)

@celery_app.task(name="sovereign.hygiene_cycle")
def run_hygiene_cycle():
    """
    Weekly Survival Hygiene Task (v13.0.0).
    Purges low-fidelity and expired memories from the Central HNSW Vault.
    """
    logger.info("[Worker-v13] Initiating Survival Hygiene Audit...")
    try:
        count = asyncio.run(SurvivalGater.purge_low_fidelity_memories())
        logger.info(f"[Worker-v13] Hygiene complete. {count} records purged.")
        return {"status": "success", "purged": count}
    except Exception as e:
        logger.error(f"[Worker-v13] Hygiene Audit failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name="sovereign.learning_cycle")
def run_learning_cycle():
    """
    Background worker for Sovereign Self-Evolution (v13.0.0).
    Synchronizes SQL-backed failure insights with the graduated Meta-Blueprint.
    """
    logger.info("[Worker-v13] Initiating Sovereign Learning Cycle...")
    try:
        count = asyncio.run(learning_system.improve())
        logger.info(f"[Worker-v13] Learning Cycle complete. {count} improvements crystallized.")
        return {"status": "success", "improvements": count}
    except Exception as e:
        logger.error(f"[Worker-v13] Learning Cycle failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Schedules the v13.0.0 self-evolution tasks."""
    # 1. Sovereign Evolution (6 hours)
    sender.add_periodic_task(
        21600.0, 
        run_learning_cycle.s(), 
        name='Sovereign Evolution (6h v13.0)'
    )
    
    # 2. Sovereign Hygiene (Weekly)
    sender.add_periodic_task(
        604800.0, 
        run_hygiene_cycle.s(), 
        name='Sovereign Hygiene (Weekly v13.0)'
    )
