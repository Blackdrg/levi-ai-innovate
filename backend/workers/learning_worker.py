import logging
from backend.celery_app import celery_app
from backend.pipelines.learning import learning_system
import asyncio

logger = logging.getLogger(__name__)

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
    """Schedules the learning cycle to run every 6 hours (configurable)."""
    # Run every 6 hours
    sender.add_periodic_task(
        21600.0, 
        run_learning_cycle.s(), 
        name='Sovereign Evolution Every 6h'
    )
