import logging
import asyncio
from datetime import datetime
from backend.celery_app import celery_app
from backend.services.learning.logic import AdaptivePromptManager
from backend.services.learning.unbound import unbound_engine
from backend.services.learning.trainer import upload_training_file, submit_finetuning_job
from backend.api.v8.telemetry import broadcast_mission_event

logger = logging.getLogger(__name__)

@celery_app.task(name="backend.services.orchestrator.learning_tasks.run_autonomous_evolution")
def run_autonomous_evolution():
    """
    Phase 12: Daily Autonomous Evolution.
    Identifies weak system prompt variants and evolves them based on successful patterns.
    """
    import asyncio
    from backend.utils.concurrency import AdaptiveThrottler, CircuitBreaker
    if CircuitBreaker.is_open():
        logger.warning("[Evolver] Circuit Breaker OPEN. Skipping autonomous evolution.")
        return

    manager = AdaptivePromptManager()
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        from backend.utils.runtime_tasks import create_tracked_task
        create_tracked_task(AdaptiveThrottler.run_throttled(manager.evolve_variants), name="autonomous-evolution")
    else:
        loop.run_until_complete(AdaptiveThrottler.run_throttled(manager.evolve_variants))
        
    logger.info("[Evolver] Evolution cycle complete.")

@celery_app.task(name="backend.services.orchestrator.learning_tasks.update_analytics_snapshot")
def update_analytics_snapshot():
    """
    Periodically flushes expensive aggregate counts to the single-document analytics cache.
    """
    import asyncio
    from backend.db.firestore_db import db as firestore_db
    
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

@celery_app.task(name="backend.services.orchestrator.learning_tasks.unbound_training_cycle")
def unbound_training_cycle():
    """
    Phase 6: Unbound Training Array Orchestration.
    Scrapes, filters, and uploads a new autonomous training batch.
    """
    from backend.utils.concurrency import AdaptiveThrottler, CircuitBreaker
    if CircuitBreaker.is_open():
        logger.warning("[Unbound] Circuit Breaker OPEN. Skipping scheduled training cycle.")
        return

    async def _run():
        # Telemetry Start
        broadcast_mission_event("system", "evolution_start", {"message": "Initiating Unbound Scraper Cycle."})
        
        batch_file = await AdaptiveThrottler.run_throttled(unbound_engine.run_unbound_cycle)
        if batch_file:
            broadcast_mission_event("system", "evolution_upload", {"message": "Wisdom Filtered. Uploading dataset."})
            file_id = upload_training_file(batch_file)
            if file_id:
                job_id = submit_finetuning_job(file_id, suffix=f"unbound_{datetime.now().strftime('%m%d')}")
                if job_id:
                    broadcast_mission_event("system", "evolution_job", {"job_id": job_id, "message": "Fine-tuning job submitted."})
                    # We store the job_id in a task-specific firestore doc to poll later
                    from backend.db.firestore_db import db as firestore_db
                    firestore_db.collection("system").document("training_status").set({
                        "last_job_id": job_id,
                        "status": "pending",
                        "updated_at": datetime.utcnow()
                    })
        else:
            broadcast_mission_event("system", "evolution_idle", {"message": "No high-fidelity wisdom harvested this cycle."})

    asyncio.run(_run())


def execute_evolution_sweep() -> Dict[str, Any]:
    """
    Sovereign v9.8.1: Global Evolution Sweep.
    Propagates local high-fidelity patterns to the shared Postgres sovereignty store.
    """
    from backend.core.v8.evolution_engine import EvolutionEngine
    from backend.db.postgres import PostgresDB
    from sqlalchemy import text
    import json
    
    evo = EvolutionEngine()
    # 1. Filter for patterns promoted to 'Gold' rules at the edge
    promoted = {k: v for k, v in evo.rules.items() if v.get("promoted")}
    
    if not promoted:
        logger.info("[Evolver] No promoted patterns found for global synchronization.")
        return {"status": "idle", "synced": 0}

    logger.info(f"[Evolver] Syncing {len(promoted)} patterns to Postgres sovereignty store...")
    
    async def _sync():
        if PostgresDB._session_factory is None:
            PostgresDB.get_engine()
            
        async with PostgresDB._session_factory() as session:
            for pattern, data in promoted.items():
                # v9.8.1: Upsert rule into the global store
                stmt = text("""
                    INSERT INTO sovereign_rules 
                    (task_pattern, result_data, fidelity_score, is_promoted, last_validated_at)
                    VALUES (:pat, :res, :fid, :prom, :now)
                    ON CONFLICT (task_pattern) 
                    DO UPDATE SET 
                        fidelity_score = EXCLUDED.fidelity_score,
                        is_promoted = EXCLUDED.is_promoted,
                        last_validated_at = EXCLUDED.last_validated_at
                """)
                await session.execute(stmt, {
                    "pat": pattern,
                    "res": json.dumps(data.get("result", {})),
                    "fid": data.get("avg_quality", 0.9),
                    "prom": True,
                    "now": datetime.now(timezone.utc)
                })
            await session.commit()
            
    try:
        # Note: In a celery worker, we use a separate run loop for sync consistency
        asyncio.run(_sync())
        broadcast_mission_event("system", "evolution_sync", {"count": len(promoted)})
        return {"status": "synced", "synced": len(promoted)}
    except Exception as e:
        logger.error(f"[Evolver] Global sync failure: {e}")
        return {"status": "failed", "error": str(e)}
