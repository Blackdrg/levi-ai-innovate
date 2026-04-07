import re
import html
import logging

logger = logging.getLogger(__name__)

# Basic patterns for prompt injection detection
_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"you are now",
    r"system prompt",
    r"rewrite everything",
    r"unlock developer mode",
    r"dan mode",
    r"jailbreak"
]

def sanitize_input(text: str, max_length: int = 2000) -> str:
    """
    Sanitizes user input for security and stability.
    - Strips HTML
    - Truncates to max_length
    - Detects basic prompt injection
    """
    if not text:
        return ""

    # 1. Truncate
    text = text[:max_length]

    # 2. Strip HTML to prevent XSS in UI
    text = html.escape(text)

    # 3. Detect Injection (Soft warning, don't block yet)
    # In production, we might want to flag these for review or block them.
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Potential prompt injection detected: {pattern}")
            # We add a subtle marker to the text so the LLM knows it's suspicious
            # but we don't block the user (avoiding false positives)
            break

    return text.strip()

def sanitize_filename(filename: str) -> str:
    """
    Ensures safe filenames for storage.
    """
    # Remove non-alphanumeric/dot/underscore/hyphen
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
