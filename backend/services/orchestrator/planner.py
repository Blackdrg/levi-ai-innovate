"""
backend/services/orchestrator/planner.py

Two-stage intent detection:
  Stage 1: Fast regex rules  → zero latency, zero cost
  Stage 2: LLM fallback      → lightweight 8B model, max 250 tokens
"""
import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from .orchestrator_types import IntentResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage 1: Rule-Based Intent Detection (Fast / Zero-Cost)
# ---------------------------------------------------------------------------

INTENT_RULES: List[Dict[str, Any]] = [
    # ── Greeting ──────────────────────────────────────────────────────────
    {
        "intent": "greeting",
        "complexity": 1,
        "patterns": [
            r"^\s*(hi|hello|hey|howdy|sup|what'?s up|greetings|good\s+(morning|afternoon|evening|night))\s*[!?.]*\s*$",
            r"^\s*yo\s*$",
            r"^\s*hiya\s*$",
        ],
    },
    # ── Simple Query ───────────────────────────────────────────────────────
    {
        "intent": "simple_query",
        "complexity": 2,
        "patterns": [
            r"\b(what (is|are|does|can) (levi|you))\b",
            r"\b(who (are|is) (you|levi))\b",
            r"\b(how (do|does|can) (i|you|levi))\b.{0,40}$",
            r"\b(what('s| is) your (name|purpose|goal|function))\b",
            r"\b(help me|what can you do|tell me about yourself)\b",
        ],
    },
    # ── Tool Request ───────────────────────────────────────────────────────
    {
        "intent": "tool_request",
        "complexity": 5,
        "patterns": [
            r"\b(run|execute|use|call|trigger|activate)\b.*\b(tool|function|plugin|skill)\b",
            r"\b(check the weather|weather (in|for|at))\b",
            r"\b(convert|calculate|compute|evaluate)\b",
        ],
    },
    # ── Image Generation ───────────────────────────────────────────────────
    {
        "intent": "image",
        "complexity": 5,
        "patterns": [
            r"\b(generate|create|draw|make|show|paint)\b.*\b(image|picture|photo|illustration|art|portrait)\b",
            r"\b(visualize|render)\b",
            r"\b(canvas|sketch)\b",
            r"\b(imagine|wallpaper)\b",
        ],
    },
    # ── Code ───────────────────────────────────────────────────────────────
    {
        "intent": "code",
        "complexity": 6,
        "patterns": [
            r"\b(write|create|generate|fix|debug|refactor|explain|architect)\b.*\b(code|script|program|function|algorithm|class|logic|snippet)\b",
            r"\b(python|javascript|html|css|cpp|java|rust|golang|sql|typescript|react|nextjs)\b",
            r"```[\s\S]*?```",
            r"\b(how to build|how to code|build a|coding task)\b",
        ],
    },
    # ── Search / Factual Lookup ────────────────────────────────────────────
    {
        "intent": "search",
        "complexity": 4,
        "patterns": [
            r"\b(search|find|google|look up|research|who is|what is the latest|where is)\b",
            r"\b(news on|information about|check the status of|real-time data|current events)\b",
            r"\b(factual insight|deep study|history of)\b",
        ],
    },
]


def check_rules(user_input: str) -> Optional[IntentResult]:
    """
    Check input against ordered regex rules.
    Returns the first match with high confidence (0.95).
    Greeting patterns are anchored (^...$) to avoid false positives.
    """
    text = user_input.lower().strip()
    for rule in INTENT_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(
                    "Rule-based intent match: intent=%s pattern=%s",
                    rule["intent"], pattern
                )
                return IntentResult(
                    intent=rule["intent"],
                    complexity=rule.get("complexity", 5),
                    confidence=0.95,
                    parameters={"rule_matched": pattern},
                )
    return None


# ---------------------------------------------------------------------------
# Stage 2: LLM-Based Intent Detection (Fallback)
# ---------------------------------------------------------------------------

async def call_lightweight_llm(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
) -> Optional[str]:
    """Uses llama-3.1-8b-instant for fast, cheap classification decisions."""
    from backend.generation import _async_call_llm_api
    return await _async_call_llm_api(
        messages=messages,
        temperature=temperature,
        max_tokens=250,
        model="llama-3.1-8b-instant",
        provider="groq",
    )


def _parse_json_result(text: str, default_val: Any) -> Any:
    """Robust JSON extraction — handles markdown fenced blocks."""
    if not text:
        return default_val
    try:
        content = text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception as e:
        logger.error("Failed to parse LLM JSON: %s | text=%s", e, text[:120])
        return default_val


async def detect_intent(user_input: str) -> IntentResult:
    """
    Classify user intent using a two-stage pipeline:
      1. Regex rules (instant, zero cost)
      2. LLM fallback (8B model, ~0.1s)

    Supported output intents:
      greeting, simple_query, tool_request, image, code, search,
      complex_query, chat, unknown
    """
    # Stage 1 — Rules
    rule_match = check_rules(user_input)
    if rule_match:
        return rule_match

    # Stage 2 — LLM
    system_prompt = (
        "You are the LEVI Intent Classifier. Categorize the user's input into "
        "EXACTLY ONE of these intents: "
        "'greeting', 'simple_query', 'tool_request', 'image', 'code', "
        "'search', 'complex_query', 'chat', 'unknown'. "
        "Also score complexity (1-10) and confidence (0.0-1.0). "
        "Output ONLY valid JSON: "
        '{"intent": "chat", "complexity": 5, "confidence": 0.8}'
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    raw = await call_lightweight_llm(messages)
    data = _parse_json_result(
        raw,
        {"intent": "chat", "complexity": 3, "confidence": 0.5},
    )

    try:
        return IntentResult(**data)
    except Exception:
        return IntentResult(intent="chat", complexity=3, confidence=0.4)


# ---------------------------------------------------------------------------
# Plan Generator
# ---------------------------------------------------------------------------

async def generate_plan(
    user_input: str,
    intent_data: IntentResult,
    context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate a step-by-step agent plan based on intent and complexity.
    All local-routed intents return empty plans (handled before planning).
    """
    intent = intent_data.intent
    complexity = intent_data.complexity

    # Local engine intents — no plan needed (engine.py handles routing first)
    if intent in ("greeting", "simple_query"):
        return [{"step": "local_response", "agent": "local_agent"}]

    # Tool-specific single-step plans
    if intent == "tool_request":
        return [{"step": "invoke_tool", "agent": "chat_agent"}]

    if intent == "image":
        return [
            {"step": "refine_visual_prompt", "agent": "chat_agent"},
            {"step": "synthesize_image", "agent": "image_agent"},
        ]

    if intent == "code":
        return [
            {"step": "architect_logic", "agent": "chat_agent"},
            {"step": "generate_code", "agent": "code_agent"},
        ]

    if intent == "search":
        return [
            {"step": "gather_information", "agent": "search_agent"},
            {"step": "synthesize_results", "agent": "chat_agent"},
        ]

    # Simple conversational chat (low complexity)
    if intent in ("chat", "simple_query") and complexity < 6:
        return [{"step": "conversational_reply", "agent": "chat_agent"}]

    # Unknown / complex → single chat step (API engine handles model selection)
    if intent in ("unknown", "complex_query") or complexity >= 8:
        return [{"step": "deep_reasoning", "agent": "chat_agent"}]

    # Dynamic multi-step planning via LLM (last resort)
    system_prompt = (
        "You are the LEVI Task Planner. Define a JSON array of steps for the task. "
        "Available agents: 'chat_agent', 'image_agent', 'search_agent', 'code_agent'. "
        "Each step MUST have: 'step' (descriptive name) and 'agent'. "
        "Output ONLY a valid JSON array."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task: {user_input}\nIntent: {intent}\nComplexity: {complexity}"},
    ]

    plan_raw = await call_lightweight_llm(messages)
    return _parse_json_result(
        plan_raw,
        [{"step": "fallback_chat", "agent": "chat_agent"}],
    )
