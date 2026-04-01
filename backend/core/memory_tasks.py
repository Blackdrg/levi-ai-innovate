"""
backend/services/orchestrator/memory_tasks.py

PHASE 47: Debounced Firestore Writes for User Memory Facts.

This module contains Celery tasks that flush the Redis write buffer
(populated by memory_utils.store_facts) to Firestore on a 30-second schedule.

Architecture:
  store_facts()  →  Redis List  →  [Beat every 30s]  →  flush_all_memory_buffers()
                                                       →  flush_memory_buffer(user_id)  →  Firestore

DEPLOYMENT NOTE:
  Requires a Celery Beat process to be running:
    celery -A backend.celery_app beat --loglevel=info
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _get_redis():
    """Get the sync Redis client. Returns (client, has_redis) tuple."""
    try:
        from backend.db.redis_client import HAS_REDIS, r
        return r, HAS_REDIS
    except Exception:
        return None, False


def _get_firestore():
    """Get the Firestore client."""
    from backend.db.firestore_db import db
    return db


def _flush_user_facts(user_id: str, redis_client) -> int:
    """
    Atomically drain the Redis buffer for a user and write to Firestore.
    Returns the number of facts flushed.
    """
    buffer_key = f"mem_buffer:{user_id}"
    db = _get_firestore()
    flushed = 0

    # Atomically pop all items from the buffer list using a pipeline
    # LRANGE + DEL is effectively atomic for our use case (single writer per user)
    pipe = redis_client.pipeline()
    pipe.lrange(buffer_key, 0, -1)   # Get all items
    pipe.delete(buffer_key)           # Atomically clear the buffer
    results = pipe.execute()

    raw_facts: List[bytes] = results[0]
    if not raw_facts:
        return 0

    logger.info(f"Flushing {len(raw_facts)} buffered facts for user '{user_id}' to Firestore.")

    # Write to Firestore using a batch for efficiency
    batch = db.batch()
    batch_count = 0
    MAX_BATCH_SIZE = 500  # Firestore batch limit

    for raw in raw_facts:
        try:
            fact_data: Dict[str, Any] = json.loads(raw)
            doc_id = fact_data.pop("fact_id", None)
            if not doc_id:
                continue

            # Convert ISO string back to datetime for Firestore
            created_at_raw = fact_data.get("created_at")
            if isinstance(created_at_raw, str):
                try:
                    fact_data["created_at"] = datetime.fromisoformat(created_at_raw)
                except ValueError:
                    fact_data["created_at"] = datetime.utcnow()
            else:
                fact_data["created_at"] = datetime.utcnow()

            doc_ref = db.collection("user_facts").document(doc_id)
            batch.set(doc_ref, fact_data)
            batch_count += 1
            flushed += 1

            # Commit in chunks if we hit the Firestore batch limit
            if batch_count >= MAX_BATCH_SIZE:
                batch.commit()
                batch = db.batch()
                batch_count = 0

        except Exception as e:
            logger.error(f"Error processing buffered fact for user '{user_id}': {e}")

    # Commit any remaining docs
    if batch_count > 0:
        try:
            batch.commit()
        except Exception as e:
            logger.error(f"Firestore batch commit failed for user '{user_id}': {e}")
            # Re-push failed facts back to Redis to avoid data loss
            if raw_facts:
                pipe2 = redis_client.pipeline()
                for raw_item in raw_facts:
                    pipe2.rpush(buffer_key, raw_item)
                pipe2.expire(buffer_key, 3600)
                pipe2.execute()
                logger.warning(f"Re-queued {len(raw_facts)} facts for user '{user_id}' after commit failure.")
            return 0

    logger.info(f"Successfully flushed {flushed} facts for user '{user_id}' to Firestore.")
    return flushed


# ── Celery Tasks ─────────────────────────────────────────────

def _get_celery_app():
    from backend.celery_app import celery_app
    return celery_app

from backend.celery_app import celery_app  # noqa: E402


@celery_app.task(
    name="backend.services.orchestrator.memory_tasks.flush_memory_buffer",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def flush_memory_buffer(self, user_id: str):
    """
    Celery task: Flush all buffered memory facts for a specific user to Firestore.
    
    Called either:
    - Directly when the buffer threshold (10 facts) is exceeded.
    - By flush_all_memory_buffers() every 30 seconds.
    """
    redis_client, has_redis = _get_redis()
    if not has_redis or redis_client is None:
        logger.warning("flush_memory_buffer: Redis unavailable, skipping flush.")
        return {"flushed": 0, "user_id": user_id}

    try:
        count = _flush_user_facts(user_id, redis_client)
        return {"flushed": count, "user_id": user_id}
    except Exception as exc:
        logger.error(f"flush_memory_buffer failed for user '{user_id}': {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name="backend.services.orchestrator.memory_tasks.flush_all_memory_buffers",
    bind=True,
)
def flush_all_memory_buffers(self):
    """
    Celery Beat periodic task (every 30s): Discover all active memory buffers
    in Redis and dispatch individual flush tasks for each user.
    
    Uses SCAN to avoid blocking Redis with KEYS in production.
    """
    redis_client, has_redis = _get_redis()
    if not has_redis or redis_client is None:
        logger.warning("flush_all_memory_buffers: Redis unavailable, skipping periodic flush.")
        return {"dispatched": 0}

    dispatched = 0
    try:
        # Use SCAN to iterate all mem_buffer:* keys (non-blocking)
        cursor = 0
        user_ids_to_flush = []
        while True:
            cursor, keys = redis_client.scan(cursor, match="mem_buffer:*", count=100)
            for key in keys:
                # Extract user_id from "mem_buffer:{user_id}"
                key_str = key.decode() if isinstance(key, bytes) else key
                user_id = key_str.removeprefix("mem_buffer:")
                if user_id:
                    user_ids_to_flush.append(user_id)
            if cursor == 0:
                break

        if not user_ids_to_flush:
            return {"dispatched": 0}

        logger.info(f"flush_all_memory_buffers: Dispatching flushes for {len(user_ids_to_flush)} users.")
        for uid in user_ids_to_flush:
            flush_memory_buffer.delay(uid)
            dispatched += 1

    except Exception as e:
        logger.error(f"flush_all_memory_buffers error: {e}", exc_info=True)

    return {"dispatched": dispatched}


@celery_app.task(
    name="backend.services.orchestrator.memory_tasks.flush_conversation_buffer",
    bind=True,
)
def flush_conversation_buffer(self):
    """
    Periodic task to flush buffered conversations from Redis to Firestore.
    Reduces write frequency to Firestore.
    """
    redis_client, has_redis = _get_redis()
    if not has_redis or redis_client is None:
        return {"flushed": 0}

    db = _get_firestore()
    flushed = 0
    
    try:
        # Atomic pull
        pipe = redis_client.pipeline()
        pipe.lrange("conv_buffer", 0, -1)
        pipe.delete("conv_buffer")
        results = pipe.execute()
        
        raw_payloads = results[0]
        if not raw_payloads:
            return {"flushed": 0}

        # Deduplicate: only the latest version of a session in this batch needs to be saved
        deduplicated = {}
        for raw in raw_payloads:
            payload = json.loads(raw)
            sid = payload.get("session_id")
            if sid:
                deduplicated[sid] = payload

        batch = db.batch()
        count = 0
        for sid, data in deduplicated.items():
            doc_ref = db.collection("conversations").document(sid)
            batch.set(doc_ref, data, merge=True)
            count += 1
            flushed += 1
            if count >= 500:
                batch.commit()
                batch = db.batch()
                count = 0
        
        if count > 0:
            batch.commit()
            
        logger.info(f"Successfully flushed {flushed} conversations from buffer.")
        return {"flushed": flushed}
        
    except Exception as e:
        logger.error(f"Error flushing conversion buffer: {e}")
        return {"error": str(e)}

@celery_app.task(
    name="backend.services.orchestrator.memory_tasks.garbage_collect_memory",
    bind=True,
)
def garbage_collect_memory(self, user_id: str):
    """
    Celery task: Run the FAISS garbage collection process for a specific user.
    Prunes expired/low-importance facts from the user's vector index.
    """
    import asyncio
    from .memory_utils import garbage_collect_index
    try:
        asyncio.run(garbage_collect_index(user_id))
        return {"status": "gc_complete", "user_id": user_id}
    except Exception as e:
        logger.error(f"Memory GC task failed for user {user_id}: {e}")
        return {"status": "failed", "error": str(e)}
@celery_app.task(
    name="backend.services.orchestrator.memory_tasks.distill_user_memories",
    bind=True,
)
def distill_user_memories(self, user_id: str):
    """
    Celery task: Run the v6 Evolutionary Distillation (Dreaming) for a user.
    Condenses fragmented facts into core traits.
    """
    from .memory_manager import MemoryManager
    import asyncio
    try:
        asyncio.run(MemoryManager.distill_core_memory(user_id))
        return {"status": "distilled", "user_id": user_id}
    except Exception as e:
        logger.error(f"Distillation task failed for {user_id}: {e}")
        return {"status": "failed", "error": str(e)}

@celery_app.task(
    name="backend.services.orchestrator.memory_tasks.run_prompt_evolution",
    bind=True,
)
def run_prompt_evolution(self):
    """
    Celery task: Trigger the autonomous prompt evolution process.
    Identifies weak system prompts and evolves them based on user success.
    """
    import asyncio
    from backend.services.learning.logic import AdaptivePromptManager
    try:
        asyncio.run(AdaptivePromptManager().evolve_variants())
        return {"status": "evolution_complete"}
    except Exception as e:
        logger.error(f"Prompt evolution task failed: {e}")
        return {"status": "failed", "error": str(e)}

@celery_app.task(
    name="backend.services.orchestrator.memory_tasks.run_global_maintenance",
    bind=True,
)
def run_global_maintenance(self):
    """
    Periodic task to discover all users and schedule memory distillation for active ones.
    """
    db = _get_firestore()
    # In a real system, we'd only pick users active in the last 24h
    # We use pagination to avoid memory issues with 10k+ sessions
    conv_ref = db.collection("conversations")
    uids = set()
    batch_size = 500
    last_doc = None

    while True:
        query = conv_ref.limit(batch_size)
        if last_doc:
            query = query.start_after(last_doc)
        
        docs = list(query.get())
        if not docs:
            break
            
        for u in docs:
            uid = u.to_dict().get("user_id")
            if uid:
                uids.add(uid)
        
        last_doc = docs[-1]
        if len(uids) >= 1000: # Safety cap for maintenance task in one run
            break
    
    for uid in uids:
        distill_user_memories.delay(uid)
        garbage_collect_memory.delay(uid)
    
    # ── Autonomous Evolution Trigger (v6 Phase 4) ──
    run_prompt_evolution.delay()
    
    return {"scheduled": len(uids)}
