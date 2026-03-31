# backend/utils/network.py
import logging
import requests
import httpx
import os
import asyncio
import time
from typing import Optional, Any, Dict, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Standard timeout for all external API calls
DEFAULT_TIMEOUT = os.getenv("API_TIMEOUT", 20)
if isinstance(DEFAULT_TIMEOUT, str):
    DEFAULT_TIMEOUT = int(DEFAULT_TIMEOUT)

# Standardized retry decorator
standard_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, Exception)),
    reraise=True
)

class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 5, recovery_time: int = 60):
        self.name = name
        self.threshold = threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL")

    def _send_alert(self, message: str):
        """Send a proactive Discord/Slack-compatible alert when circuit trips."""
        if not self.webhook_url:
            return
        try:
            payload = {
                "content": f"🚨 **LEVI-AI ALERT**: Circuit Breaker **[{self.name}]** {message}",
                "username": "LEVI Monitoring",
            }
            requests.post(self.webhook_url, json=payload, timeout=2.0)
        except Exception as e:
            logger.error(f"Failed to send circuit-breaker alert for {self.name}: {e}")

    def call(self, func: Callable, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "HALF-OPEN"
                logger.info(f"Circuit {self.name} is now HALF-OPEN.")
            else:
                raise RuntimeError(f"Circuit {self.name} is OPEN. Try again later.")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except requests.exceptions.HTTPError as e:
            # 429 doesn't break the circuit, it just means wait
            if e.response is not None and e.response.status_code == 429:
                logger.warning(f"Rate limit hit in {self.name}. Circuit remains {self.state}.")
                raise e
            self.on_failure()
            raise e
        except Exception as e:
            self.on_failure()
            raise e

    async def async_call(self, func: Callable, *args, **kwargs):
        """Async support for circuit breaking."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "HALF-OPEN"
                logger.info(f"Circuit {self.name} is now HALF-OPEN.")
            else:
                raise RuntimeError(f"Circuit {self.name} is OPEN. Try again later.")

        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            # Standardize 429 check for both requests and httpx
            is_rate_limit = False
            if hasattr(e, "response") and e.response is not None:
                status_code = getattr(e.response, "status_code", None)
                if status_code == 429:
                    is_rate_limit = True

            if is_rate_limit:
                logger.warning(f"Async Rate limit hit in {self.name}. Circuit remains {self.state}.")
                raise e

            self.on_failure()
            raise e

    def on_success(self):
        if self.state == "HALF-OPEN":
            logger.info(f"Circuit {self.name} is now CLOSED.")
        self.failures = 0
        self.state = "CLOSED"

    def on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            was_open = self.state == "OPEN"
            self.state = "OPEN"
            if not was_open:
                logger.critical(f"Circuit {self.name} has OPENED due to {self.failures} failures.")
                self._send_alert("TRIPPED! Transitioned to OPEN state due to repeated failures.")

# Global circuit breakers (single source of truth — circuit_breaker.py is deprecated)
ai_service_breaker = CircuitBreaker("AI_SERVICE", threshold=3, recovery_time=30)
groq_breaker = CircuitBreaker("Groq", threshold=3, recovery_time=30)
together_breaker = CircuitBreaker("TogetherAI", threshold=5, recovery_time=60)

def safe_request(method: str, url: str, **kwargs) -> requests.Response:
    """
    Standardized wrapper for requests with timeout, logging, and error handling.
    """
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    
    request_id = kwargs.pop("request_id", "unknown")
    
    try:
        logger.info(f"API Request [{request_id}]: {method} {url}")
        response = requests.request(method, url, **kwargs)
        
        if response.status_code == 429:
            logger.warning(f"Rate limit hit for {url} (ID: {request_id})")
        
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "???"
        logger.error(f"HTTP Error {status_code} for {url} (ID: {request_id}): {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Network Error for {url} (ID: {request_id}): {e}")
        raise
async def async_safe_request(method: str, url: str, **kwargs) -> httpx.Response:
    """
    Phase 43: Async wrapper for parallel inference.
    Uses httpx for non-blocking I/O.
    """
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    
    request_id = kwargs.pop("request_id", "unknown")
    
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Async API Request [{request_id}]: {method} {url}")
            response = await client.request(method, url, **kwargs)
            
            if response.status_code == 429:
                logger.warning(f"Async Rate limit hit for {url} (ID: {request_id})")
            
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(f"Async HTTP Error {status_code} for {url} (ID: {request_id}): {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Async Network Error for {url} (ID: {request_id}): {e}")
            raise
