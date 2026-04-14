"""
backend/core/memory_tasks.py

Sovereign Memory Tasks v15.0-GA.
Handles asynchronous memory maintenance, distillation, and background re-indexing.
Utilizes Postgres SQL Fabric for primary persistence.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.db.postgres import PostgresDB
from backend.db.models import UserFact, Mission
from backend.memory.vector_store import SovereignVectorStore
from backend.core.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

def _get_redis():
    """Get the sync Redis client. Returns (client, has_redis) tuple."""
    try:
        from backend.db.redis import HAS_REDIS, r
        return r, HAS_REDIS
    except Exception:
        return None, False

# ── Celery Tasks ─────────────────────────────────────────────

from backend.celery_app import celery_app

@celery_app.task(
    name="backend.core.memory_tasks.flush_memory_buffer",
    bind=True,
    max_retries=3,
)
def flush_memory_buffer(self, user_id: str):
    """
    Sovereign v15: Flush buffered memory facts for a specific user to Postgres.
    """
    redis_client, has_redis = _get_redis()
    if not has_redis or redis_client is None:
        return {"flushed": 0, "user_id": user_id}

    buffer_key = f"mem_buffer:{user_id}"
    try:
        # Atomic drain
        pipe = redis_client.pipeline()
        pipe.lrange(buffer_key, 0, -1)
        pipe.delete(buffer_key)
        results = pipe.execute()
        
        raw_facts = results[0]
        if not raw_facts: return {"flushed": 0}

        count = 0
        async def process_flush():
             nonlocal count
             async with PostgresDB._session_factory() as session:
                for raw in raw_facts:
                    data = json.loads(raw)
                    new_fact = UserFact(
                        user_id=user_id,
                        fact=data.get("fact"),
                        category=data.get("category", "general"),
                        importance=data.get("importance", 0.5)
                    )
                    session.add(new_fact)
                    count += 1
                await session.commit()
        
        import asyncio
        asyncio.run(process_flush())
        
        return {"flushed": count, "user_id": user_id}
    except Exception as exc:
        logger.error(f"flush_memory_buffer failure: {exc}")
        raise self.retry(exc=exc)

@celery_app.task(
    name="backend.core.memory_tasks.garbage_collect_memory",
    bind=True,
)
def garbage_collect_memory(self, user_id: str):
    """
    Rebuilds the local FAISS index from Postgres truth.
    """
    import asyncio
    try:
        asyncio.run(SovereignVectorStore.reindex_user_memory(user_id))
        return {"status": "reindexed", "user_id": user_id}
    except Exception as e:
        logger.error(f"Memory GC task failed for user {user_id}: {e}")
        return {"status": "failed", "error": str(e)}

@celery_app.task(
    name="backend.core.memory_tasks.distill_user_memories",
    bind=True,
    max_retries=2,
)
def distill_user_memories(self, user_id: str):
    """
    Sovereign v15: Memory Distillation (Dreaming).
    Crystallizes recent episodic/mid-term patterns into permanent traits.
    """
    import asyncio
    
    logger.info(f"[Dreaming] Executing v15 distillation for user: {user_id}")
    try:
        manager = MemoryManager()
        success = asyncio.run(manager.dream(user_id))
        
        if success:
             redis_client, has_redis = _get_redis()
             if has_redis and redis_client:
                 redis_client.delete(f"user:{user_id}:dream_ready")
                 
        return {"status": "crystallized" if success else "no_material", "user_id": user_id}
    except Exception as e:
        logger.error(f"[Dreaming] Distillation breach for {user_id}: {e}")
        return {"status": "failed", "error": str(e)}

@celery_app.task(
    name="backend.core.memory_tasks.dream_all_users",
    bind=True,
)
def dream_all_users(self):
    """
    Discovery loop for users ready for dreaming (Distillation).
    Now fallback to Postgres activity if Redis flags are missing.
    """
    redis_client, has_redis = _get_redis()
    scheduled = 0

    try:
        import asyncio
        async def fetch_uids():
            if has_redis and redis_client:
                cursor = 0
                keys = []
                while True:
                    cursor, batch = redis_client.scan(cursor, match="user:*:dream_ready", count=100)
                    for k in batch: keys.append(k)
                    if cursor == 0: break
                if keys:
                    return [k.decode().split(":")[1] for k in keys if isinstance(k, bytes)]

            # Fallback to recent mission activity
            async with PostgresDB._session_factory() as session:
                from sqlalchemy import select
                stmt = select(Mission.user_id).distinct().limit(50)
                res = await session.execute(stmt)
                return res.scalars().all()

        uids = asyncio.run(fetch_uids())
        for uid in uids:
            distill_user_memories.delay(uid)
            scheduled += 1
                
        return {"scheduled": scheduled}
    except Exception as e:
        logger.error(f"[Dreaming] Discovery loop failed: {e}")
        return {"error": str(e)}

@celery_app.task(
    name="backend.core.memory_tasks.run_global_maintenance",
    bind=True,
)
def run_global_maintenance(self):
    """
    Sovereign v15: Global Maintenance Sweep.
    """
    import asyncio
    async def get_active_users():
        from sqlalchemy import select
        async with PostgresDB._session_factory() as session:
            stmt = select(Mission.user_id).distinct().limit(100)
            res = await session.execute(stmt)
            return res.scalars().all()
    
    try:
        uids = asyncio.run(get_active_users())
        for uid in uids:
            garbage_collect_memory.delay(uid)
        return {"scheduled": len(uids)}
    except Exception as e:
        logger.error(f"[Maintenance] Sweep drift: {e}")
        return {"error": str(e)}

@celery_app.task(
    name="backend.core.memory_tasks.run_survival_hygiene",
    bind=True,
)
def run_survival_hygiene(self):
    """
    Sovereign v15: Resonance Survival Hygiene.
    Prunes low-resonance noise using the non-linear decay engine.
    """
    import asyncio
    from backend.memory.resonance import MemoryResonance
    
    async def process_hygiene():
        from sqlalchemy import select
        from backend.db.postgres_db import get_read_session
        async with get_read_session() as session:
            stmt = select(UserFact.user_id).distinct().limit(200)
            res = await session.execute(stmt)
            uids = res.scalars().all()
            
        for uid in uids:
            try:
                # 1. Fetch current facts
                facts = await SovereignVectorStore.get_all_facts(uid)
                if not facts: continue
                
                # 2. Apply Decay (Resonance Filter)
                filtered = MemoryResonance.apply_decay(facts)
                
                # 3. If pruning occurred, update Vector Store
                if len(filtered) < len(facts):
                    logger.info(f"✨ [Resonance] Pruned {len(facts) - len(filtered)} faded memories for {uid}")
                    await SovereignVectorStore.sync_from_facts(uid, filtered)
                    
            except Exception as e:
                logger.error(f"[Resonance] Hygiene failure for {uid}: {e}")

    try:
        asyncio.run(process_hygiene())
        return {"status": "hygiene_complete"}
    except Exception as e:
        logger.error(f"[Maintenance] Resonance sweep failed: {e}")
        return {"error": str(e)}
