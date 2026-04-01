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
# Stage 1: Scoring-Based Brain Orchestration Engine
# ---------------------------------------------------------------------------

class BrainScorer:
    """
    Sovereign Decision Logic: Routes queries based on keywords + pattern scoring.
    """
    KEYWORDS = {
        "search": ["search", "latest", "news", "find", "google", "research", "current", "weather", "look up"],
        "document": ["document", "pdf", "file", "according to", "pdf", "paper", "upload", "page", "context"],
        "chat": ["hi", "hello", "how are you", "tell me", "talk", "chat", "speak"]
    }

    @staticmethod
    def calculate_scores(user_input: str) -> Dict[str, float]:
        text = user_input.lower()
        scores = {"chat": 0.1, "search": 0.0, "document": 0.0}

        # 1. Keyword Presence (No API)
        for route, keywords in BrainScorer.KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[route] += 0.3
        
        # 2. Pattern Matching
        if re.search(r"\b(pdf|docx|txt|file|paper)\b", text): scores["document"] += 0.4
        if re.search(r"\b(current|latest|news|live|real-time)\b", text): scores["search"] += 0.4
        if re.search(r"^\s*(hi|hello|hey|yo|howdy)\s*", text): scores["chat"] += 0.5

        return scores

def detect_orchestration_route(user_input: str) -> Dict[str, Any]:
    """
    Determines the target engine route (chat | search | document).
    """
    scores = BrainScorer.calculate_scores(user_input)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_route, confidence = sorted_scores[0]
    
    # Cap confidence at 0.95 for internal logic
    confidence = min(confidence, 0.95)
    
    return {
        "route": top_route,
        "reason": f"Keywords matched for {top_route}",
        "confidence": confidence
    }

INTENT_RULES: List[Dict[str, Any]] = [
    {
        "intent": "greeting",
        "complexity_level": 0,
        "cost_weight": "low",
        "patterns": [
            r"^\s*(hi|hello|hey|howdy|sup|what'?s up|greetings|good\s+(morning|afternoon|evening|night))\s*[!?.]*\s*$",
            r"^\s*yo\s*$",
            r"^\s*hiya\s*$",
        ],
    },
    {
        "intent": "simple_query",
        "complexity_level": 1,
        "cost_weight": "low",
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
        "complexity_level": 3,
        "cost_weight": "high",
        "patterns": [
            r"\b(generate|create|draw|make|show|paint)\b.*\b(image|picture|photo|illustration|art|portrait)\b",
            r"\b(visualize|render)\b",
            r"\b(imagine|wallpaper)\b",
        ],
    },
    {
        "intent": "code",
        "complexity_level": 3,
        "cost_weight": "high",
        "patterns": [
            r"\b(write|create|generate|fix|debug|refactor|explain|architect)\b.*\b(code|script|program|function|algorithm|class|logic|snippet)\b",
            r"\b(python|javascript|html|css|cpp|java|rust|golang|sql|typescript|react|nextjs)\b",
            r"```[\s\S]*?```",
        ],
    },
    {
        "intent": "logic",
        "complexity_level": 2,
        "cost_weight": "medium",
        "patterns": [
            r"\b(calculate|compute|solve|math|equation|formula|percent|projection)\b",
            r"\b(what is [0-9]+ (\+|\*|\/|\-|plus|times|minus|divided by) [0-9]+)\b",
        ],
    },
    {
        "intent": "search",
        "complexity_level": 2,
        "cost_weight": "medium",
        "patterns": [
            r"\b(search|find|google|look up|research|who is|what is the latest|where is)\b",
            r"\b(news on|information about|check the status of|real-time data|current events)\b",
        ],
    },
]

def check_rules(user_input: str) -> Optional[IntentResult]:
    text = user_input.lower().strip()
    
    # 1. First, check specific static rules
    for rule in INTENT_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return IntentResult(
                    intent_type=rule["intent"],
                    complexity_level=rule.get("complexity_level", 2),
                    estimated_cost_weight=rule.get("cost_weight", "medium"),
                    confidence_score=0.95,
                    parameters={"rule_matched": pattern},
                )
    
    # 2. If no rule matches, use scoring system
    orch = detect_orchestration_route(user_input)
    return IntentResult(
        intent_type=orch["route"],
        complexity_level=2 if orch["route"] in ("search", "document") else 1,
        estimated_cost_weight="medium",
        confidence_score=orch["confidence"],
        parameters={"routing": orch}
    )

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
    # 1. High-Speed Rule-Based Detection
    rule_match = check_rules(user_input)
    if rule_match: return rule_match

    system_prompt = (
        "You are the LEVI Adaptive Decision Engine. Classify this request:\n"
        "Output ONLY JSON: {\n"
        "  'intent_type': 'greeting|factual|search|creative|technical|action|chat|hybrid|document',\n"
        "  'complexity_level': 0-3,\n"
        "  'estimated_cost_weight': 'low|medium|high',\n"
        "  'confidence_score': 0.0-1.0\n"
        "}"
    )
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
    
    # 2. Sovereign Local Detection (Primary Fallback)
    from .local_engine import handle_local_sync
    local_raw = await handle_local_sync(messages)
    if local_raw:
        data = _parse_json_result(local_raw, None)
        if data:
            logger.info("[Planner] Intent detected via local engine.")
            return IntentResult(**data)

    # 3. Cloud LLM Fallback (Secondary Fallback)
    try:
        raw = await call_lightweight_llm(messages)
        data = _parse_json_result(raw, {
            "intent_type": "chat", 
            "complexity_level": 2, 
            "estimated_cost_weight": "medium",
            "confidence_score": 0.5
        })
        logger.info("[Planner] Intent detected via Cloud LLM.")
        return IntentResult(**data)
    except Exception:
        return IntentResult(intent_type="chat", complexity_level=2, confidence_score=0.3)

# ---------------------------------------------------------------------------
# Plan Generator (The Deterministic Core)
# ---------------------------------------------------------------------------

async def generate_plan(user_input: str, intent_data: IntentResult, context: Dict[str, Any]) -> ExecutionPlan:
    """
    Adaptive Decision-Based Planning.
    Assigns engines based on complexity level (0-3).
    """
    intent = intent_data.intent_type
    level = intent_data.complexity_level
    steps: List[PlanStep] = []
    memory_needed: List[str] = ["user_profile"]

    # ── Level 0: Trivial (Zero Engines) ──────────────────────────────────
    if level == 0:
        # Plans with no steps signify the Brain should return from Cache or Static logic
        return ExecutionPlan(intent=intent, steps=[], complexity_level=0)

    # ── Level 1: Simple (Single cheap engine) ───────────────────────────
    if level == 1:
        steps.append(PlanStep(
            description="Direct contextual processing",
            agent="local_agent",
            critical=True
        ))

    # ── Level 2: Moderate (LLM + Supporting engine) ────────────────────
    elif level == 2:
        memory_needed.append("session_mood")
        if intent == "search":
             steps.append(PlanStep(description="Knowledge lookup", agent="search_agent", critical=True))
             steps.append(PlanStep(description="Contextual synthesis", agent="chat_agent", critical=True))
        elif intent == "document":
             steps.append(PlanStep(description="Internal document retrieval", agent="document_agent", critical=True))
             steps.append(PlanStep(description="Contextual Q&A synthesis", agent="chat_agent", critical=True))
        elif intent == "logic":
             steps.append(PlanStep(description="Logic verification", agent="python_repl_agent", critical=True))
             steps.append(PlanStep(description="Conversational expansion", agent="chat_agent", critical=True))
        elif intent == "hybrid":
             steps.append(PlanStep(description="Knowledge lookup", agent="search_agent", critical=True))
             steps.append(PlanStep(description="Conversational expansion", agent="chat_agent", critical=True))
        else:
            steps.append(PlanStep(description="Moderate reasoning synthesis", agent="chat_agent", critical=True))

    # ── Level 3: Complex (Multi-engine pipeline) ───────────────────────
    elif level == 3:
        memory_needed.extend(["session_mood", "long_term_memory"])
        
        if intent == "image":
            steps.append(PlanStep(description="Visual prompt architecting", agent="chat_agent", critical=False))
            steps.append(PlanStep(description="High-fidelity rendering", agent="image_agent", critical=True))
        
        elif intent == "code":
            steps.append(PlanStep(description="Architectural solution", agent="code_agent", critical=True))
            steps.append(PlanStep(description="Implementation verification", agent="python_repl_agent", critical=False))
        
        else: # Complex Reasoning/Creative
            steps.append(PlanStep(description="Contextual research", agent="search_agent", critical=False))
            steps.append(PlanStep(description="Synthesis & Refinement", agent="chat_agent", critical=True))

    # Safety Fallback
    if not steps:
        steps.append(PlanStep(description="Conversational synthesis", agent="chat_agent", critical=True))

    return ExecutionPlan(
        intent=intent,
        steps=steps,
        memory_needed=memory_needed,
        complexity_level=level
    )
