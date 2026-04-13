"""
Sovereign Circuit Breaker v15.0.
Prevents system-wide failure by isolating degraded agents and services.
"""

import time
import logging
import asyncio
from enum import Enum
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    CLOSED = "CLOSED"     # Normal operation
    OPEN = "OPEN"         # Requests blocked
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class CircuitBreaker:
    """
    Sovereign v15.0: Fault-Tolerant Circuit Breaker.
    """
    def __init__(
        self, 
        name: str, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 60,
        expected_exception: Any = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            # 1. State Check & Recovery Logic
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    logger.info(f"🔄 [Breaker:{self.name}] Transitioning to HALF_OPEN (Testing recovery)")
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise RuntimeError(f"⚠️ [Breaker:{self.name}] Circuit is OPEN. Request blocked.")

        # 2. Execution
        try:
            result = await func(*args, **kwargs)
            
            # 3. Success Handling
            async with self._lock:
                if self.state == CircuitState.HALF_OPEN:
                    logger.info(f"✅ [Breaker:{self.name}] Transitioning to CLOSED (System Healthy)")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
            return result
            
        except self.expected_exception as e:
            # 4. Failure Handling
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    logger.critical(f"🚨 [Breaker:{self.name}] Failure threshold {self.failure_threshold} reached. Opening Circuit.")
                    self.state = CircuitState.OPEN
                
                logger.warning(f"⚠️ [Breaker:{self.name}] Failure recorded ({self.failure_count}/{self.failure_threshold}): {e}")
                raise e

# Global Registry for Breakers
_registry: Dict[str, CircuitBreaker] = {}

def get_breaker(name: str, **kwargs) -> CircuitBreaker:
    if name not in _registry:
        _registry[name] = CircuitBreaker(name, **kwargs)
    return _registry[name]
