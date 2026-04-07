import asyncio
import logging
import time
from typing import Dict, Any, Callable, Optional
from backend.redis_client import r as redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

class AdaptiveThrottler:
    """
    Sovereign v13.1.0-Hardened-PROD: Graduated Task Loop Control.
    Hard-gates background tasks to 4 parallel slots to ensure GPU stability.
    """
    _semaphore: Optional[asyncio.BoundedSemaphore] = None
    _MAX_CONCURRENT = 4

    @classmethod
    def get_semaphore(cls) -> asyncio.BoundedSemaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.BoundedSemaphore(cls._MAX_CONCURRENT)
        return cls._semaphore

    @classmethod
    async def run_throttled(cls, task_func: Callable, *args, **kwargs):
        """Executes a task within the concurrency limit."""
        sem = cls.get_semaphore()
        async with sem:
            try:
                return await task_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[AdaptiveThrottler] Task failed: {e}")
                return None

class CircuitBreaker:
    """
    Sovereign v13.1.0-Hardened-PROD: General Adaptive Circuit Breaker.
    Pauses non-critical background services if infrastructure latency spikes.
    """
    _FAILURE_COUNT = 0
    _THRESHOLD = 5
    _PAUSE_UNTIL = 0

    @classmethod
    def is_open(cls) -> bool:
        if cls._PAUSE_UNTIL > time.time():
            return True
        return False

    @classmethod
    def record_failure(cls, service_name: str = "Unknown"):
        cls._FAILURE_COUNT += 1
        if cls._FAILURE_COUNT >= cls._THRESHOLD:
            logger.critical(f"[CircuitBreaker] {service_name} Loop OPENED due to repeated failures. Pausing 5m.")
            cls._PAUSE_UNTIL = time.time() + 300
            cls._FAILURE_COUNT = 0

    @classmethod
    def record_success(cls):
        cls._FAILURE_COUNT = 0
