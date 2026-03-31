"""
backend/services/orchestrator/planner.py

Deterministic Task Planner v2.0
Generates validated ExecutionPlans for all LEVI-AI inputs.
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from .orchestrator_types import IntentResult, ExecutionPlan, PlanStep

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage 1: Rule-Based Intent Detection
# ---------------------------------------------------------------------------

INTENT_RULES: List[Dict[str, Any]] = [
    {
        "intent": "greeting",
        "complexity": 1,
        "patterns": [
            r"^\s*(hi|hello|hey|howdy|sup|what'?s up|greetings|good\s+(morning|afternoon|evening|night))\s*[!?.]*\s*$",
            r"^\s*yo\s*$",
            r"^\s*hiya\s*$",
        ],
    },
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
    {
        "intent": "image",
        "complexity": 5,
        "patterns": [
            r"\b(generate|create|draw|make|show|paint)\b.*\b(image|picture|photo|illustration|art|portrait)\b",
            r"\b(visualize|render)\b",
            r"\b(imagine|wallpaper)\b",
        ],
    },
    {
        "intent": "code",
        "complexity": 7,
        "patterns": [
            r"\b(write|create|generate|fix|debug|refactor|explain|architect)\b.*\b(code|script|program|function|algorithm|class|logic|snippet)\b",
            r"\b(python|javascript|html|css|cpp|java|rust|golang|sql|typescript|react|nextjs)\b",
            r"```[\s\S]*?```",
        ],
    },
    {
        "intent": "logic",
        "complexity": 4,
        "patterns": [
            r"\b(calculate|compute|solve|math|equation|formula|percent|projection)\b",
            r"\b(what is [0-9]+ (\+|\*|\/|\-|plus|times|minus|divided by) [0-9]+)\b",
        ],
    },
    {
        "intent": "search",
        "complexity": 5,
        "patterns": [
            r"\b(search|find|google|look up|research|who is|what is the latest|where is)\b",
            r"\b(news on|information about|check the status of|real-time data|current events)\b",
        ],
    },
]

def check_rules(user_input: str) -> Optional[IntentResult]:
    text = user_input.lower().strip()
    for rule in INTENT_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return IntentResult(
                    intent=rule["intent"],
                    complexity=rule.get("complexity", 5),
                    confidence=0.95,
                    parameters={"rule_matched": pattern},
                )
    return None

# ---------------------------------------------------------------------------
# Stage 2: LLM Fallback (Intent Detection)
# ---------------------------------------------------------------------------

async def call_lightweight_llm(messages: List[Dict[str, str]], temperature: float = 0.3) -> Optional[str]:
    from backend.generation import _async_call_llm_api
    return await _async_call_llm_api(
        messages=messages,
        temperature=temperature,
        max_tokens=250,
        model="llama-3.1-8b-instant",
        provider="groq",
    )

def _parse_json_result(text: str, default_val: Any) -> Any:
    if not text: return default_val
    try:
        content = text.strip()
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception:
        return default_val

async def detect_intent(user_input: str) -> IntentResult:
    rule_match = check_rules(user_input)
    if rule_match: return rule_match

    system_prompt = (
        "You are the LEVI Intent Classifier. Categorize into ONE: "
        "'greeting', 'simple_query', 'image', 'code', 'logic', 'search', 'chat', 'unknown'. "
        "Output ONLY JSON: {\"intent\": \"chat\", \"complexity\": 5, \"confidence\": 0.8}"
    )
    try:
        raw = await call_lightweight_llm([{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}])
        data = _parse_json_result(raw, {"intent": "chat", "complexity": 3, "confidence": 0.5})
        return IntentResult(**data)
    except Exception:
        return IntentResult(intent="chat", complexity=3, confidence=0.3)

# ---------------------------------------------------------------------------
# Plan Generator (The Deterministic Core)
# ---------------------------------------------------------------------------

async def generate_plan(user_input: str, intent_data: IntentResult, context: Dict[str, Any]) -> ExecutionPlan:
    """
    Constructs a deterministic ExecutionPlan based on intent and complexity.
    Unifies all interactions into the same structural flow.
    """
    intent = intent_data.intent
    complexity = intent_data.complexity
    steps: List[PlanStep] = []
    memory_needed: List[str] = ["user_profile", "session_mood"]

    # 1. Deterministic Step Assignment
    if intent in ("greeting", "simple_query"):
        steps.append(PlanStep(
            description="Generate immediate context-aware response",
            agent="local_agent",
            critical=True
        ))

    elif intent == "image":
        memory_needed.append("visual_preferences")
        steps.append(PlanStep(
            description="Construct high-fidelity visual prompt",
            agent="chat_agent",
            tool_input={"task": "visual_prompt_refining"},
            critical=False
        ))
        steps.append(PlanStep(
            description="Trigger image generation job",
            agent="image_agent",
            critical=True
        ))

    elif intent == "code":
        memory_needed.append("coding_history")
        steps.append(PlanStep(
            description="Architect and implement solution",
            agent="code_agent",
            critical=True
        ))
        # Add verification step for high-complexity code
        if complexity >= 8:
            steps.append(PlanStep(
                description="Verify logic and edge cases via Python REPL",
                agent="python_repl_agent",
                critical=False
            ))

    elif intent == "logic":
        steps.append(PlanStep(
            description="Perform precise computational verification",
            agent="python_repl_agent",
            critical=True
        ))

    elif intent == "search":
        steps.append(PlanStep(
            description="Execute real-time research with Tavily",
            agent="search_agent",
            critical=True
        ))
        steps.append(PlanStep(
            description="Synthesize findings with philosophical depth",
            agent="chat_agent",
            critical=False
        ))

    # 2. Dynamic Planning Fallback for complex/chat tasks
    if not steps or intent == "chat":
        steps.append(PlanStep(
            description="Synthesize personalized conversational response",
            agent="chat_agent",
            critical=True
        ))

    return ExecutionPlan(
        intent=intent,
        steps=steps,
        memory_needed=memory_needed,
        estimated_complexity=complexity
    )
