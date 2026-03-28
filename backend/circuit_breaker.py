import time
import logging
from functools import wraps
from typing import Callable, Any
import requests
import os

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF-OPEN
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL")

    def _send_alert(self, message: str):
        """Send a proactive alert to the configured webhook."""
        if not self.webhook_url:
            return
            
        try:
            # Simple Discord/Slack compatible JSON payload
            payload = {
                "content": f"🚨 **LEVI-AI ALERT**: Circuit Breaker **[{self.name}]** {message}",
                "username": "LEVI Monitoring"
            }
            # Short timeout to avoid blocking the main thread
            requests.post(self.webhook_url, json=payload, timeout=2.0)
        except Exception as e:
            logger.error(f"Failed to send alert for {self.name}: {e}")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info(f"Circuit Breaker [{self.name}] entering HALF-OPEN state")
            else:
                raise Exception(f"Circuit Breaker [{self.name}] is OPEN. Skipping call.")

        try:
            result = func(*args, **kwargs)
            if self.state != "CLOSED":
                logger.info(f"Circuit Breaker [{self.name}] RECOVERED and is now CLOSED")
                self.state = "CLOSED"
                self.failures = 0
            return result
        except Exception as e:
            # Only count true "failures". Rate limits (429) are usually handled by retries
            # but if they persist, they can trip the circuit. 
            self.failures += 1
            self.last_failure_time = time.time()
            
            error_msg = str(e)
            if hasattr(e, "response") and e.response is not None:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"

            logger.warning(f"Circuit Breaker [{self.name}] failure {self.failures}/{self.failure_threshold}: {error_msg}")
            
            if self.failures >= self.failure_threshold:
                if self.state != "OPEN":
                    logger.error(f"Circuit Breaker [{self.name}] THRESHOLD REACHED. State changed to OPEN.")
                    self._send_alert("TRIPPED! Transitioned to OPEN state due to repeated failures.")
                self.state = "OPEN"
            
            raise e

# Instances for different APIs
groq_breaker = CircuitBreaker("Groq", failure_threshold=3, recovery_timeout=30)
together_breaker = CircuitBreaker("TogetherAI", failure_threshold=5, recovery_timeout=60)
         
