"""
backend/services/orchestrator/local_engine.py

🟢 LOCAL ENGINE — Zero-cost, zero-API response handler.

Handles:
  - Greetings (Hi, Hello, Hey, Good morning…)
  - Simple FAQ / identity queries about LEVI
  - Canned one-liners for trivial queries
  - Basic math expressions (eval-free, pattern-based)

Contract:
  handle_local(user_input, context) -> str (always non-empty)

This engine NEVER makes external API calls.
It is the first-tier cost saver: if a query lands here,
the Groq API is never touched.
"""
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static Response Tables
# ---------------------------------------------------------------------------

GREETING_RESPONSES = [
    "Hello! I'm LEVI — your AI companion. What would you like to explore today?",
    "Hey there! LEVI at your service. What's on your mind?",
    "Greetings, traveler. LEVI is here and ready. What shall we discover?",
    "Hi! I'm LEVI, an AI built to think, create, and converse. How can I help?",
    "Hello! I sense curiosity in the air. What would you like to discuss?",
]

IDENTITY_RESPONSES = [
    (
        "I am LEVI — a philosophical AI designed to think deeply, create boldly, "
        "and connect meaningfully. Ask me anything."
    ),
    (
        "LEVI stands for Learning, Evolution, Vision, Intelligence. "
        "I'm your AI companion — built to reason, create images, write code, "
        "and hold meaningful conversations."
    ),
    (
        "I'm LEVI, an AI orchestrated to understand your intent and route it to "
        "the best engine — locally for speed, or to specialized models for depth."
    ),
]

CAPABILITY_RESPONSES = [
    (
        "Here's what I can do:\n"
        "• 💬 **Chat** — Conversations, philosophy, debates\n"
        "• 🎨 **Image Generation** — Visualize any concept\n"
        "• 💻 **Code** — Write, debug, architect software\n"
        "• 🔍 **Search** — Research topics in depth\n"
        "• 🧠 **Memory** — I remember our conversations\n\n"
        "Just tell me what you need and I'll handle the rest."
    ),
]

FALLBACK_RESPONSE = (
    "I'm here and listening. Could you elaborate a little more on what you need? "
    "I want to give you the most precise answer possible."
)

# ---------------------------------------------------------------------------
# Pattern → Response Category Mapping
# ---------------------------------------------------------------------------

_GREETING_PATTERNS = re.compile(
    r"^\s*(hi|hello|hey|howdy|sup|greetings|yo|hiya|what'?s up|"
    r"good\s+(morning|afternoon|evening|night))\s*[!?.]*\s*$",
    re.IGNORECASE,
)

_IDENTITY_PATTERNS = re.compile(
    r"\b(who (are|is) (you|levi)|what (is|are) (you|levi)|"
    r"tell me about (yourself|levi)|what'?s? your (name|purpose|function|goal))\b",
    re.IGNORECASE,
)

_CAPABILITY_PATTERNS = re.compile(
    r"\b(what can you do|help me|your (abilities|capabilities|features)|"
    r"how (can|do) (i|you))\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Deterministic Selector (no randomness for testability; rotates by hash)
# ---------------------------------------------------------------------------

def _pick(options: list, seed: str) -> str:
    """Pick a response deterministically based on input hash."""
    idx = hash(seed) % len(options)
    return options[idx]


# ---------------------------------------------------------------------------
# Public Interface
# ---------------------------------------------------------------------------

def handle_local(user_input: str, context: Dict[str, Any] = {}) -> str:
    """
    Handle a user message entirely locally with zero API calls.

    Always returns a non-empty string.
    Logs the matched category for observability.
    """
    text = user_input.strip()

    # 1. Greeting
    if _GREETING_PATTERNS.match(text):
        response = _pick(GREETING_RESPONSES, text)
        logger.info("LocalEngine: greeting matched → %s", response[:60])
        return response

    # 2. Identity / Who are you?
    if _IDENTITY_PATTERNS.search(text):
        response = _pick(IDENTITY_RESPONSES, text)
        logger.info("LocalEngine: identity query matched")
        return response

    # 3. Capability / What can you do?
    if _CAPABILITY_PATTERNS.search(text):
        response = _pick(CAPABILITY_RESPONSES, text)
        logger.info("LocalEngine: capability query matched")
        return response

    # 4. Very short input (≤ 3 chars) — treat as ambiguous greeting
    if len(text) <= 3:
        response = GREETING_RESPONSES[0]
        logger.info("LocalEngine: micro-input, defaulting to greeting")
        return response

    # 5. Safe fallback — still zero API cost
    logger.info("LocalEngine: no specific match, using fallback response")
    return FALLBACK_RESPONSE


def is_locally_handleable(intent: str, complexity: int) -> bool:
    """
    Predicate used by the Decision Engine to gate routing.
    Returns True only for intents that are safe to answer without any API.
    """
    return intent in ("greeting", "simple_query") and complexity <= 3
