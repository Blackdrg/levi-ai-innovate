import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF-OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info(f"Circuit Breaker [{self.name}] entering HALF-OPEN state")
            else:
                raise Exception(f"Circuit Breaker [{self.name}] is OPEN. Skipping call.")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF-OPEN":
                self.state = "CLOSED"
                self.failures = 0
                logger.info(f"Circuit Breaker [{self.name}] recovered and CLOSED")
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            logger.warning(f"Circuit Breaker [{self.name}] failure {self.failures}/{self.failure_threshold}: {e}")
            
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit Breaker [{self.name}] is now OPEN")
            
            raise e

# Instances for different APIs
groq_breaker = CircuitBreaker("Groq", failure_threshold=3, recovery_timeout=30)
together_breaker = CircuitBreaker("TogetherAI", failure_threshold=5, recovery_timeout=60)
         
