import logging
import random
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Standard standardized timeout for all external API calls
DEFAULT_TIMEOUT = 20

# Standardized retry decorator for AI service calls
standard_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, Exception)),
    reraise=True
)

def safe_request(method, url, **kwargs):
    """
    Standardized wrapper for requests with timeout and manual error handling.
    """
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    
    try:
        response = requests.request(method, url, **kwargs)
        if response.status_code == 429:
            logger.warning(f"Rate limit hit for {url}")
            # Could implement automatic sleep-and-retry here if needed
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed to {url}: {e}")
        raise


def compute_backoff_delay(
    attempt: int,
    strategy: str = "exp_backoff_jitter",
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter_ratio: float = 0.25,
) -> float:
    """Returns a bounded retry delay that de-synchronizes bursts under load."""
    bounded_attempt = max(1, int(attempt))
    normalized = (strategy or "exp_backoff_jitter").lower()

    if normalized == "fixed":
        delay = base_delay
    else:
        delay = min(max_delay, base_delay * (2 ** (bounded_attempt - 1)))

    if "jitter" in normalized:
        jitter_span = delay * max(0.0, jitter_ratio)
        delay += random.uniform(0.0, jitter_span)

    return round(min(max_delay, delay), 3)
