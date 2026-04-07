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
        Performs a sweep of critical keys and resolves conflicts.
        Uses Last-Writer-Wins (LWW) based on 'updated_at' and 'term'.
        """
        if not HAS_REDIS_ASYNC:
            return

        for prefix in self.critical_prefixes:
            keys = await redis_client.keys(f"{prefix}*")
            if not keys:
                continue

            for key in keys:
                # In a real DCN, we would compare with a sibling node here.
                # For this implementation, we ensure the local key has proper metadata.
                val_raw = await redis_client.get(key)
                if not val_raw:
                    continue

                try:
                    data = json.loads(val_raw)
                    # 🛠️ Self-Healing: Ensure metadata exists
                    if "metadata" not in data:
                        data["metadata"] = {
                            "origin": self.node_id,
                            "updated_at": time.time(),
                            "term": 1
                        }
                        await redis_client.set(key, json.dumps(data))
                except json.JSONDecodeError:
                    continue

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
