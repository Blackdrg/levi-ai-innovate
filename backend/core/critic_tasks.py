import logging
import json
import asyncio
from typing import List, Dict, Any
from backend.celery_app import celery_app
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.core.v8.critic import ReflectionEngine

logger = logging.getLogger(__name__)

@celery_app.task(
    name="backend.core.critic_tasks.process_failure_queue",
    bind=True,
    max_retries=2
)
def process_failure_queue(self):
    """
    Sovereign v9.8.1: Autonomous Self-Healing Task.
    Drains the 'sovereign:failure_queue' from Redis and triggers the ReflectionEngine
    to suggest system-wide patches or prompt optimizations.
    """
    if not HAS_REDIS or redis_client is None:
        logger.error("[Self-Healing] Redis disconnected. Aborting healing cycle.")
        return {"status": "failed", "reason": "redis_unavailable"}

    # 1. Atomic Drain
    pipe = redis_client.pipeline()
    pipe.lrange("sovereign:failure_queue", 0, -1)
    pipe.delete("sovereign:failure_queue")
    results = pipe.execute()
    
    raw_failures = results[0]
    if not raw_failures:
        logger.info("[Self-Healing] Queue empty. No healing needed.")
        return {"status": "idle"}

    failures = []
    for raw in raw_failures:
        try:
            failures.append(json.loads(raw))
        except:
            continue

    logger.warning(f"[Self-Healing] Processing {len(failures)} logic failures for recursive patching...")
    
    # 2. Reflection & Patching
    async def _patch():
        critic = ReflectionEngine()
        # V9.8: suggest_system_patch performs LLM-driven root cause analysis
        # and suggests improvements to the prompt blueprint or intent model.
        await critic.suggest_system_patch(failures)
        
    try:
        asyncio.run(_patch())
        return {"status": "processed", "failure_count": len(failures)}
    except Exception as e:
        logger.error(f"[Self-Healing] Patch cycle drift: {e}")
        # On failure, we could re-queue, but for now we just log to avoid loops
        return {"status": "failed", "error": str(e)}
