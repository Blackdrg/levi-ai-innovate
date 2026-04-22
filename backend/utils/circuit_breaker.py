import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """
    Sovereign Circuit Breaker v16.2.
    Prevents cascading failures by temporarily disabling failing services.
    """
    def __init__(self, name: str, threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED

    def _get_redis(self):
        from backend.db.redis import get_redis_client
        return get_redis_client()

    async def _get_state(self) -> CircuitState:
        r = self._get_redis()
        if r:
            state = r.get(f"circuit:{self.name}:state")
            if state:
                return CircuitState(state)
        return self.state

    async def _set_state(self, state: CircuitState):
        self.state = state
        r = self._get_redis()
        if r:
            r.set(f"circuit:{self.name}:state", state.value)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        current_state = await self._get_state()
        
        if current_state == CircuitState.OPEN:
            last_fail = 0
            r = self._get_redis()
            if r:
                last_fail_raw = r.get(f"circuit:{self.name}:last_failure")
                last_fail = float(last_fail_raw) if last_fail_raw else 0
            else:
                last_fail = self.last_failure_time

            if time.time() - last_fail > self.recovery_timeout:
                await self._set_state(CircuitState.HALF_OPEN)
                logger.info(f"🔄 [CircuitBreaker] {self.name} attempting recovery (HALF_OPEN).")
            else:
                logger.warning(f"🚫 [CircuitBreaker] {self.name} is OPEN. Rejecting call.")
                raise Exception(f"Circuit Breaker {self.name} is open.")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success logic
            if (await self._get_state()) == CircuitState.HALF_OPEN:
                logger.info(f"✅ [CircuitBreaker] {self.name} recovered (CLOSED).")
                await self._set_state(CircuitState.CLOSED)
                r = self._get_redis()
                if r: r.delete(f"circuit:{self.name}:failures")
                self.failure_count = 0
            
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            r = self._get_redis()
            if r:
                fails = r.incr(f"circuit:{self.name}:failures")
                r.set(f"circuit:{self.name}:last_failure", self.last_failure_time)
                if fails >= self.threshold:
                    await self._set_state(CircuitState.OPEN)
                    logger.critical(f"🚨 [CircuitBreaker] {self.name} TRIPPED (OPEN). Failures: {fails}")
            else:
                if self.failure_count >= self.threshold:
                    self.state = CircuitState.OPEN
                    logger.critical(f"🚨 [CircuitBreaker] {self.name} TRIPPED (OPEN). Failures: {self.failure_count}")
            
            raise e

# Global Circuit Registry (Sovereign v22.1 Resilience Matrix)
agent_breaker    = CircuitBreaker("AgentSystem", threshold=5, recovery_timeout=120)
neo4j_breaker    = CircuitBreaker("Neo4jStorage", threshold=3, recovery_timeout=30)
postgres_breaker = CircuitBreaker("PostgresStorage", threshold=10, recovery_timeout=30)
redis_breaker    = CircuitBreaker("RedisConsensus", threshold=5, recovery_timeout=15)
faiss_breaker    = CircuitBreaker("FAISSVectorDB", threshold=3, recovery_timeout=30)
ollama_breaker   = CircuitBreaker("OllamaInference", threshold=5, recovery_timeout=60)
bridge_breaker   = CircuitBreaker("SerialTelemetryBridge", threshold=3, recovery_timeout=30)
