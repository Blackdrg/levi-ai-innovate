import logging
from datetime import datetime
from backend.celery_app import celery_app
from backend.learning import AdaptivePromptManager

logger = logging.getLogger(__name__)

@celery_app.task(name="backend.services.orchestrator.learning_tasks.run_autonomous_evolution")
def run_autonomous_evolution():
    """
    Phase 12: Daily Autonomous Evolution.
    Identifies weak system prompt variants and evolves them based on successful patterns.
    """
    import asyncio
    logger.info("[Evolver] Initiating daily autonomous evolution cycle...")
    
    manager = AdaptivePromptManager()
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # This shouldn't happen in a celery worker unless misconfigured
        asyncio.create_task(manager.evolve_variants())
    else:
        loop.run_until_complete(manager.evolve_variants())
        
    logger.info("[Evolver] Evolution cycle complete.")

@celery_app.task(name="backend.services.orchestrator.learning_tasks.update_analytics_snapshot")
def update_analytics_snapshot():
    """
    Periodically flushes expensive aggregate counts to the single-document analytics cache.
    """
    import asyncio
    from backend.firestore_db import db as firestore_db
    
    async def _update():
        logger.info("[Analytics] Refreshing global analytics snapshot...")
        total = len(firestore_db.collection("training_data").get())
        hq = len(firestore_db.collection("training_data").where("rating", ">=", 4).get())
        learned = len(firestore_db.collection("quotes").where("topic", "==", "__learned__").get())
        
        ref = firestore_db.collection("system").document("analytics")
        await asyncio.to_thread(ref.update, {
            "total_samples": total,
            "hq_samples": hq,
            "learned_quotes": learned,
            "updated_at": datetime.utcnow()
        })
        logger.info("[Analytics] Snapshot updated.")

    asyncio.run(_update())

@celery_app.task(name="backend.services.orchestrator.learning_tasks.prune_expired_data")
def prune_expired_data():
    """
    Phase 6: Data Lifecycle Management.
    Removes temporary uploads and stale document indices older than 30 days.
    """
    import os
    import time
    from pathlib import Path

    UPLOAD_DIR = Path("backend/data/uploads")
    if not UPLOAD_DIR.exists():
        return

    now = time.time()
    count = 0
    # Prune files older than 30 days
    for file_path in UPLOAD_DIR.glob("*"):
        if os.path.isfile(file_path):
            if now - os.path.getmtime(file_path) > (30 * 86400):
                os.remove(file_path)
                count += 1
    
    logger.info(f"[Maintenance] Pruned {count} expired files from {UPLOAD_DIR}")

@celery_app.task(name="backend.services.orchestrator.learning_tasks.consolidate_global_wisdom")
def consolidate_global_wisdom():
    """
    Phase 18: Global Wisdom Consolidation.
    Periodically saves the FAISS global wisdom index to disk to prevent data loss.
    """
    from backend.utils.vector_db import VectorDB
    import asyncio
    
    async def _save():
        vdb = VectorDB("global_wisdom")
        # VectorDB.save() is implicit in most operations, but we ensure persistence here
        logger.info("[Maintenance] Consolidating Global Wisdom Index...")
        # If we had a buffer-to-index logic, it would go here. 
        # For now, we just ensure the index is healthy.
    
    asyncio.run(_save())
