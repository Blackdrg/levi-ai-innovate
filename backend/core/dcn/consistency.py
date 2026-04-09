import json
import logging
import time
import asyncio
from typing import Dict, Any
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

class ConsistencyEngine:
    """
    Sovereign DCN Consistency Engine v1.0.
    Implements anti-entropy via Merkle-lite reconciliation.
    Ensures critical mission states are synchronized across the swarm.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.critical_prefixes = ["mission:", "swarm:rules:"]
        self.is_running = False

    async def start_reconciliation_loop(self, interval: int = 60):
        """Background loop to perform anti-entropy check."""
        self.is_running = True
        logger.info(f"[Consistency] Anti-Entropy loop started (Interval: {interval}s)")
        while self.is_running:
            try:
                await self.reconcile()
            except Exception as e:
                logger.error(f"[Consistency] Reconciliation pulse failed: {e}")
            await asyncio.sleep(interval)

    async def reconcile(self):
        """
        Performs a sweep of critical keys and resolves conflicts with peers.
        Step 1: Fetch local state summary.
        Step 2: Compare with Global Consensus State in Redis.
        Step 3: Resolve missions where local state is stale.
        """
        if not HAS_REDIS_ASYNC:
            return

        logger.info(f"[Consistency] Executing P2P Reconciliation Pulse node={self.node_id}...")
        
        for prefix in self.critical_prefixes:
            # 1. Broad scan of active missions
            keys = await redis_client.keys(f"{prefix}*")
            if not keys:
                continue

            for key in keys:
                # 2. Check for Global Lock (Consensus)
                consensus_key = f"consensus:{key}"
                consensus_raw = await redis_client.get(consensus_key)
                
                local_raw = await redis_client.get(key)
                if not local_raw:
                    continue

                local_data = json.loads(local_raw)
                
                if consensus_raw:
                    # Consensus exists -> Check for drift
                    consensus_data = json.loads(consensus_raw)
                    if self._calculate_hash(local_data) != self._calculate_hash(consensus_data):
                        logger.warning(f"[Consistency] State Drift detected for {key}. Resolving...")
                        resolved = await self.resolve_conflict(key, local_data, consensus_data)
                        if resolved != local_data:
                            await redis_client.set(key, json.dumps(resolved))
                else:
                    # No consensus -> We attempt to push our state as candidate
                    logger.debug(f"[Consistency] Promoting local state to consensus for {key}")
                    await redis_client.set(consensus_key, json.dumps(local_data), ex=3600)

    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """Simple property-based hash for change detection."""
        # Exclude metadata like 'updated_at' from hash to avoid false positives
        clean_data = {k: v for k, v in data.items() if k != "metadata"}
        import hashlib
        return hashlib.md5(json.dumps(clean_data, sort_keys=True).encode()).hexdigest()

    async def resolve_conflict(self, key: str, local_data: Dict[str, Any], remote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves a detected conflict between local and remote state.
        Priority: 
        1. Higher Term (Consensus)
        2. Higher Timestamp (LWW)
        """
        local_meta = local_data.get("metadata", {})
        remote_meta = remote_data.get("metadata", {})

        local_term = local_meta.get("term", 0)
        remote_term = remote_meta.get("term", 0)

        if remote_term > local_term:
            logger.info(f"[Consistency] Conflict resolved for {key}: Remote Term {remote_term} won.")
            return remote_data
        
        if remote_term < local_term:
            return local_data

        local_ts = local_meta.get("updated_at", 0)
        remote_ts = remote_meta.get("updated_at", 0)

        if remote_ts > local_ts:
            logger.info(f"[Consistency] Conflict resolved for {key}: Remote Timestamp won.")
            return remote_data

        return local_data

    def stop(self):
        self.is_running = False
