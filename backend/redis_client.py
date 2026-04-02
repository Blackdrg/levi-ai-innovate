import redis
import os
import logging
from typing import Optional, Any, List

logger = logging.getLogger(__name__)

# --- Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

class SovereignCache:
    """
    Sovereign Persistence Layer (Redis).
    Hardened for high-concurrency state and backpressure management.
    """
    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Retrieves and initializes the Redis client singleton."""
        if cls._instance is not None:
            return cls._instance
        
        try:
            logger.info(f"[Redis] Connecting to Sovereign Cache at {REDIS_HOST}:{REDIS_PORT}")
            cls._instance = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Connectivity check
            cls._instance.ping()
            return cls._instance
        except Exception as e:
            logger.error(f"[Redis] Critical connection failure: {e}")
            # Fallback to a mock-like behavior if Redis is unavailable in local dev
            return redis.Redis(host='localhost', port=REDIS_PORT, db=REDIS_DB)

    @classmethod
    def get(cls, key: str, namespace: str = "global") -> Optional[str]:
        client = cls.get_client()
        full_key = f"sovereign:{namespace}:{key}"
        return client.get(full_key)

    @classmethod
    def set(cls, key: str, value: Any, ex: int = 3600, namespace: str = "global"):
        client = cls.get_client()
        full_key = f"sovereign:{namespace}:{key}"
        client.set(full_key, value, ex=ex)

    @classmethod
    def delete(cls, key: str, namespace: str = "global"):
        client = cls.get_client()
        full_key = f"sovereign:{namespace}:{key}"
        client.delete(full_key)

# Global Accessor
cache = SovereignCache
