import logging
import json
import random
from typing import Dict, Any, List, Optional
from backend.db.redis import get_async_redis_client, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

class ReplayBuffer:
    """
    Sovereign v16.2: Persistent Replay Buffer for Cognitive Evolution.
    Uses Redis Lists to ensure learning data persists across reboots.
    """
    REDIS_KEY = "sovereign:replay:experiences"

    def __init__(self, capacity: int = 5000):
        self.capacity = capacity
        # We use the sync client for basic add/sample if needed, but async is preferred
        from backend.db.redis import get_redis_client
        self._sync_client = get_redis_client()

    def add(self, state: Dict[str, Any], action: Dict[str, Any], reward: float, next_state: Dict[str, Any]):
        """Adds an experience tuple (S, A, R, S') to the persistent buffer."""
        if not self._sync_client: return
        
        experience = {
            "state": state,
            "action": action,
            "reward": reward,
            "next_state": next_state
        }
        
        try:
            # Atomic add and trim
            pipe = self._sync_client.pipeline()
            pipe.lpush(self.REDIS_KEY, json.dumps(experience))
            pipe.ltrim(self.REDIS_KEY, 0, self.capacity - 1)
            pipe.execute()
        except Exception as e:
            logger.error(f"[ReplayBuffer] Failed to persist experience: {e}")

    def sample(self, batch_size: int) -> List[Dict[str, Any]]:
        """Samples a batch of experiences from persistent storage."""
        if not self._sync_client: return []
        
        try:
            # For simplicity, we fetch all and sample. In v16.2.1 we could use SRANDMEMBER if it were a set.
            # But we want order/trimming, so we use list.
            raw_data = self._sync_client.lrange(self.REDIS_KEY, 0, -1)
            if not raw_data: return []
            
            count = min(len(raw_data), batch_size)
            selected = random.sample(raw_data, count)
            return [json.loads(x) for x in selected]
        except Exception as e:
            logger.error(f"[ReplayBuffer] Sample error: {e}")
            return []

    def clear(self):
        if self._sync_client:
            self._sync_client.delete(self.REDIS_KEY)

    def __len__(self):
        if not self._sync_client: return 0
        return self._sync_client.llen(self.REDIS_KEY)

# Global Replay Buffer for the Evolution Engine
global_replay_buffer = ReplayBuffer(capacity=5000)
