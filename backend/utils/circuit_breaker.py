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

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
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
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"✅ [CircuitBreaker] {self.name} recovered (CLOSED).")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.threshold:
                self.state = CircuitState.OPEN
                logger.critical(f"🚨 [CircuitBreaker] {self.name} TRIPPED (OPEN). Failure count: {self.failure_count}")
            
            raise e

# Global Circuit Registry
agent_breaker = CircuitBreaker("AgentSystem", threshold=5, recovery_timeout=120)
neo4j_breaker = CircuitBreaker("Neo4jStorage", threshold=3, recovery_timeout=30)
postgres_breaker = CircuitBreaker("PostgresStorage", threshold=10, recovery_timeout=30)
