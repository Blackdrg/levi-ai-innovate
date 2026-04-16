# backend/utils/network.py
import logging
import requests
import httpx
import os
import time
from backend.utils.egress import EgressProxy
from typing import Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Standard timeout for all external API calls
DEFAULT_TIMEOUT = os.getenv("API_TIMEOUT", 20)
if isinstance(DEFAULT_TIMEOUT, str):
    DEFAULT_TIMEOUT = int(DEFAULT_TIMEOUT)

# Audit Point 06: SSRF Protection
ALLOWED_DOMAINS = [
    "localhost", "127.0.0.1",
    "api.openai.com", "api.anthropic.com", "api.groq.com", "api.together.xyz",
    "github.com", "api.github.com",
    "google.com"
]

def is_url_allowed(url: str) -> bool:
    """Delegates to Sovereing EgressProxy for SSRF protection."""
    return EgressProxy.validate_target(url)

# Standardized retry decorator
standard_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, Exception)),
    reraise=True
)

from backend.utils.circuit_breaker import (
    agent_breaker as ai_service_breaker, 
    neo4j_breaker, 
    postgres_breaker as redis_breaker
)
groq_breaker = ai_service_breaker # Aliasing for legacy compatibility
together_breaker = ai_service_breaker

def safe_request(method: str, url: str, **kwargs) -> requests.Response:
    """
    Standardized wrapper for requests with timeout, logging, and error handling.
    """
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    
    request_id = kwargs.pop("request_id", "unknown")
    
    if not is_url_allowed(url):
        logger.error(f"[Shield] Blocked SSRF attempt to unauthorized domain: {url}")
        raise RuntimeError("Network Egress Blocked: Unauthorized domain.")

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
    
    if not is_url_allowed(url):
        logger.error(f"[Shield] Blocked Async SSRF attempt to unauthorized domain: {url}")
        raise RuntimeError("Network Egress Blocked: Unauthorized domain.")

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
