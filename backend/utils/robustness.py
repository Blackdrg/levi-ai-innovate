"""
backend/utils/robustness.py

Standardized resilience utilities for the LEVI AI platform.
Includes:
- Centralized Retry System (Tenacity)
- Async Timeout Handlers
- Circuit Breaker integration
"""

import asyncio
import logging
import os
from functools import wraps
from typing import Any, Callable, Type, Union, Tuple

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

# --- Configuration ---
DEFAULT_RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
DEFAULT_TIMEOUT = int(os.getenv("API_TIMEOUT", 20))

# --- Retry System ---

def standard_retry(
    attempts: int = DEFAULT_RETRY_ATTEMPTS,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = (Exception,)
):
    """
    Standardized async retry decorator.
    Uses exponential backoff: 2s, 4s, 8s...
    """
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )

# --- Timeout Handling ---

class TimeoutHandler:
    """ Context manager and utility for async timeouts. """
    
    @staticmethod
    async def run_with_timeout(coro: Any, seconds: int = DEFAULT_TIMEOUT) -> Any:
        try:
            return await asyncio.wait_for(coro, timeout=seconds)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {seconds}s")
            raise TimeoutError(f"Operation timed out after {seconds}s")

def with_timeout(seconds: int = DEFAULT_TIMEOUT):
    """ Decorator for async functions to enforce a timeout. """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await TimeoutHandler.run_with_timeout(func(*args, **kwargs), seconds)
        return wrapper
    return decorator

# --- Error Mapping (Future Proofing) ---

def wrap_service_error(service_name: str):
    """
    Decorator to catch service-specific errors and wrap them in LEVIException.
    To be used in Phase 2 for central error handling.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                from .exceptions import LEVIException
                logger.error(f"Error in {service_name}: {str(e)}")
                raise LEVIException(
                    message=f"Service failure in {service_name}",
                    status_code=500,
                    error_code=f"{service_name.upper()}_FAILURE"
                )
        return wrapper
    return decorator
