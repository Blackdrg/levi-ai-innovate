import logging
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
