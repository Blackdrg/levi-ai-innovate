"""
Sovereign Memory Garbage Collector v14.0.
Periodically prunes expired memory markers and cleans up consistency events.
"""

import asyncio
import logging
import time
from typing import List, Tuple
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

class MemoryGC:
    def __init__(self, interval_seconds: int = 3600):
        self.interval = interval_seconds
        self.manager = MemoryManager()

    async def run_loop(self):
        """
        Main GC loop.
        """
        logger.info(f"[GC] Memory Garbage Collector starting with interval {self.interval}s")
        while True:
            try:
                if HAS_REDIS:
                    await self.prune_consistency_events()
                    await self.process_gc_markers()
            except Exception as e:
                logger.error(f"[GC] Error in GC loop: {e}")
            
            await asyncio.sleep(self.interval)

    async def prune_consistency_events(self):
        """
        Cleans up old mcm:event:* keys that haven't been touched.
        (Redis handles TTL, so we mainly check for orphans or sync state).
        """
        # Redis setex already handles TTL, so we don't need manual pruning for mcm:event:*
        pass

    async def process_gc_markers(self):
        """
        Finds mcm:gc:* markers and triggers cleanup in derived stores.
        """
        logger.info("[GC] Processing GC markers...")
        keys = redis_client.keys("mcm:gc:*")
        if not keys:
            return

        for key in keys:
            try:
                # Key format: mcm:gc:{user_id}:{item_id}
                parts = key.split(":")
                if len(parts) < 4:
                    continue
                
                user_id = parts[2]
                item_id = parts[3]
                
                # Check if TTL has expired (the key existence itself means it's still "marked")
                # But schedule_gc sets a TTL. When the key DISAPPEARS, we should clean up.
                # Wait, the current logic is that the marker is the target.
                # If the marker exists, we clean it up now.
                
                logger.info(f"[GC] Cleaning up memory item {item_id} for user {user_id}")
                
                # Perform actual cleanup
                await self.cleanup_item(user_id, item_id)
                
                # Remove the marker
                redis_client.delete(key)
                
            except Exception as e:
                logger.error(f"[GC] Failed to process marker {key}: {e}")

    async def cleanup_item(self, user_id: str, item_id: str):
        """
        Performs the actual deletion in derived stores (Neo4j, FAISS, etc).
        """
        # Placeholder for actual cleanup logic
        # In a real system, we'd query for the item by ID and delete it.
        # self.manager.delete_item(user_id, item_id)
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gc = MemoryGC()
    asyncio.run(gc.run_loop())
