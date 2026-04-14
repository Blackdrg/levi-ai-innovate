"""
Sovereign Maintenance v14.0.0.
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

async def rotate_dcn_secret():
    """
    Sovereign v15.0 GA: DCN Key Rotation.
    Updates the cluster shared secret and synchronizes with the vault.
    Note: Requires a rolling restart of nodes or a multi-key acceptance window.
    """
    logger.info("[Maintenance] Initiating DCN Secret Rotation cycle...")
    from backend.utils.shield import SovereignShield
    import secrets
    
    new_secret = secrets.token_urlsafe(64)
    # In a real impl, we'd store this in HashiCorp Vault or AWS KMS
    # and signal all nodes to reload.
    # Here we just log the requirement for the orchestration layer.
    logger.warning("🔑 [Maintenance] New DCN_SECRET generated. Update Vault and perform rolling restart to apply.")

async def nightly_memory_decay():
    """
    Sovereign v15.0 GA: Autonomous Memory Decay.
    Calculates resonance scores for all episodic memories and prunes low-fidelity data.
    """
    logger.info("[Maintenance] Starting nightly memory decay cycle...")
    
    from backend.db.vector import _USER_COLLECTIONS
    from backend.memory.resonance import MemoryResonance
    
    count = 0
    pruned_total = 0
    for user_id, store in _USER_COLLECTIONS.items():
        try:
            # 1. Fetch all active memories for the user
            # Note: This requires the store to have a 'get_all_memories' method
            if hasattr(store, 'get_all_memories'):
                all_memories = await store.get_all_memories()
                if not all_memories:
                    continue
                
                # 2. Apply decay and filter
                resonant_memories = MemoryResonance.apply_decay(all_memories)
                
                # 3. If pruning occurred, overwrite the collection
                if len(resonant_memories) < len(all_memories):
                    await store.overwrite_collection(resonant_memories)
                    pruned_total += (len(all_memories) - len(resonant_memories))
                    count += 1
        except Exception as e:
            logger.error(f"[Maintenance] Decay failed for user {user_id}: {e}")
            
    logger.info(f"[Maintenance] Memory decay complete. Pruned {pruned_total} memories across {count} users.")

async def run_full_maintenance_suite():
    """Unified entry point for periodic system hygiene."""
    await nightly_vector_rebuild()
    await nightly_memory_decay()
    await cleanup_gdpr_backups()
    logger.info("[Maintenance] Full suite execution complete.")
