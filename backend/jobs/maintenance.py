"""
Sovereign Maintenance v13.1.0.
Handles nightly FAISS rebuilds and GDPR erasure compliance.
"""

import logging
import time
from backend.db.vector import _USER_COLLECTIONS
from backend.db.redis import r as redis_sync, HAS_REDIS

logger = logging.getLogger(__name__)

async def nightly_vector_rebuild():
    """
    Triggers physical compaction of vector indices.
    Iterates through active cached collections and invokes rebuild_index.
    """
    logger.info("[Maintenance] Starting nightly vector rebuild...")
    
    # In a production scenario, we might want to discover all index names 
    # from the filesystem, but for now we process active ones.
    count = 0
    for key, store in _USER_COLLECTIONS.items():
        try:
            await store.rebuild_index()
            count += 1
        except Exception as e:
            logger.error(f"[Maintenance] Rebuild failed for {key}: {e}")
            
    logger.info(f"[Maintenance] Nightly rebuild complete. Processed {count} collections.")

async def cleanup_gdpr_backups():
    """
    Removes soft-delete IDs from Redis that are older than 30 days.
    This fulfills the 'retained up to 30 days for recovery' requirement.
    """
    if not HAS_REDIS or not redis_sync:
        return

    logger.info("[Maintenance] Cleaning up expired GDPR backups (30+ days)...")
    
    # We use a ZSET to track deletion time: gdpr:deleted:timestamps:{index_name}
    # For simplicity in this implementation, we'll iterate through known collections.
    now = time.time()
    retention_period = 30 * 24 * 60 * 60 # 30 days
    
    for key in _USER_COLLECTIONS.keys():
        ts_key = f"gdpr:deleted:timestamps:{key}"
        # Remove members with score (timestamp) older than (now - retention_period)
        removed = redis_sync.zremrangebyscore(ts_key, 0, now - retention_period)
        if removed > 0:
            logger.info(f"[Maintenance] Pruned {removed} expired recovery IDs from {key}.")

def schedule_maintenance():
    """
    Entry point for Celery or background scheduler.
    """
    # This would be called by a Celery beat task
    pass
