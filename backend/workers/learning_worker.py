import logging
from backend.celery_app import celery_app
from backend.pipelines.learning import learning_system
import asyncio

logger = logging.getLogger(__name__)

@celery_app.task(name="sovereign.hygiene_cycle")
def run_hygiene_cycle():
    """
    Weekly Survival Hygiene Task.
    Purges low-fidelity and expired memories from the central vector store.
    """
    logger.info("[Worker] Starting Survival Hygiene Audit...")
    try:
        from backend.services.learning.hygiene import SurvivalGater
        loop = asyncio.get_event_loop()
        count = loop.run_until_complete(SurvivalGater.purge_low_fidelity_memories())
        
        logger.info(f"[Worker] Hygiene complete. {count} records purged.")
        return {"status": "success", "purged": count}
    except Exception as e:
        logger.error(f"[Worker] Hygiene Audit failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.task(name="sovereign.learning_cycle")
def run_learning_cycle():
    """
    Background worker for Sovereign Self-Evolution.
    Polls failure logs and converts them into optimized prompt blueprints.
    """
    logger.info("[Worker] Starting Sovereign Learning Cycle...")
    
    try:
        # Run the async improvement logic in the sync Celery worker context
        loop = asyncio.get_event_loop()
        count = loop.run_until_complete(learning_system.improve())
        
        logger.info(f"[Worker] Learning Cycle complete. {count} improvements generated.")
        return {"status": "success", "improvements": count}
    except Exception as e:
        logger.error(f"[Worker] Learning Cycle failed: {e}")
        return {"status": "error", "message": str(e)}

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Schedules the learning cycle to run every 6 hours and hygiene every week."""
    # 1. Sovereign Evolution (6 hours)
    sender.add_periodic_task(
        21600.0, 
        run_learning_cycle.s(), 
        name='Sovereign Evolution Every 6h'
    )
    
    # 2. Sovereign Hygiene (Weekly - 604800s)
    sender.add_periodic_task(
        604800.0, 
        run_hygiene_cycle.s(), 
        name='Sovereign Hygiene Every Week'
    )
