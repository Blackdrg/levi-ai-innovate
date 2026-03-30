import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from .orchestrator_types import IntentResult

logger = logging.getLogger(__name__)

# --- Rule-Based Intent Detection (Fast/Zero-Cost) ---

INTENT_RULES = [
    {
        "intent": "image",
        "patterns": [
            r"\b(generate|create|draw|make|show|paint)\b.*\b(image|picture|photo|illustration|art|portrait)\b",
            r"\b(visualize|render)\b",
            r"\b(canvas|sketch)\b",
            r"\b(imagine|wallpaper)\b"
        ]
    },
    {
        "intent": "code",
        "patterns": [
            r"\b(write|create|generate|fix|debug|refactor|explain|architect)\b.*\b(code|script|program|function|algorithm|class|logic|snippet)\b",
            r"\b(python|javascript|html|css|cpp|java|rust|golang|sql|typescript|react|nextjs)\b",
            r"```[\s\S]*?```", # Markdown code blocks
            r"\b(how to build|how to code|build a|coding task)\b"
        ]
    },
    {
        "intent": "search",
        "patterns": [
            r"\b(search|find|google|look up|research|who is|what is the latest|where is)\b",
            r"\b(news on|information about|check the status of|real-time data|current events)\b",
            r"\b(factual insight|deep study|history of)\b"
        ]
    }
]

def check_rules(user_input: str) -> Optional[IntentResult]:
    """Checks input against regex rules for high-confidence matches."""
    text = user_input.lower().strip()
    for rule in INTENT_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text):
                logger.info(f"Rule-based match: {rule['intent']} (Pattern: {pattern})")
                return IntentResult(
                    intent=rule["intent"],
                    complexity=5, # Default moderate complexity for rule matches
                    confidence=0.95,
                    parameters={"rule_matched": pattern}
                )
    return None

# --- LLM-Based Intent Detection (Fallback/Complex) ---

async def call_lightweight_llm(messages: List[Dict[str, str]], temperature: float = 0.5) -> Optional[str]:
    """Uses a lightweight model (llama-3.1-8b) for quick decisions."""
    from backend.generation import _async_call_llm_api
    return await _async_call_llm_api(
        messages=messages,
        temperature=temperature,
        max_tokens=250,
        model="llama-3.1-8b-instant",
        provider="groq"
    )

async def detect_intent(user_input: str) -> IntentResult:
    """Classify the user intent using Rules -> LLM fallback."""
    # 1. Try Rules First
    rule_match = check_rules(user_input)
    if rule_match:
        return rule_match

    # 2. LLM Fallback
    system_prompt = (
        "You are the LEVI Intent Classifier. Categorize the user's input into one of: "
        "'chat' (conversational), 'image' (visual generation), 'search' (fact-finding/research), "
        "'code' (programming), 'multi_step' (requires multiple actions). "
        "Also assess complexity from 1-10. "
        "Logic: "
        "- If the user wants a picture/art, use 'image'. "
        "- If the user asks for code/logic/programming, use 'code'. "
        "- If the user asks for facts/news/research, use 'search'. "
        "- If it's a general conversation, use 'chat'. "
        "Output ONLY JSON: {\"intent\": \"category\", \"complexity\": 5, \"confidence\": 0.8}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    res_json = await call_lightweight_llm(messages)
    if not res_json:
        return IntentResult(intent="chat", complexity=1, confidence=0.5)
    
def _parse_json_result(text: str, default_val: Any) -> Any:
    """Robust parsing of LLM JSON results with support for markdown fencing."""
    if not text: return default_val
    
    try:
        # 1. Clean fenced blocks
        content = text.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        # 2. Parse
        return json.loads(content.strip())
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON: {e} | Original: {text[:100]}...")
        return default_val

async def detect_intent(user_input: str) -> IntentResult:
    """Classify the user intent using Rules -> LLM fallback."""
    # 1. Try Rules First
    rule_match = check_rules(user_input)
    if rule_match:
        return rule_match

    # 2. LLM Fallback
    system_prompt = (
        "You are the LEVI Intent Classifier. Categorize the user's input into one of: "
        "'chat', 'image', 'search', 'code'. "
        "Also assess complexity (1-10) and confidence (0-1). "
        "Output ONLY JSON: {\"intent\": \"category\", \"complexity\": 5, \"confidence\": 0.8}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    res_raw = await call_lightweight_llm(messages)
    data = _parse_json_result(res_raw, {"intent": "chat", "complexity": 1, "confidence": 0.5})
    
    try:
        return IntentResult(**data)
    except Exception:
        return IntentResult(intent="chat", complexity=3, confidence=0.4)

async def generate_plan(user_input: str, intent_data: IntentResult, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate a step-by-step plan based on intent and complexity."""
    intent = intent_data.intent
    complexity = intent_data.complexity

    # Simple Chat Path
    if intent == "chat" and complexity < 6:
        return [{"step": "conversational_reply", "agent": "chat_agent"}]
    
    # Tool-Specific Paths
    if intent == "image":
        return [
            {"step": "refine_visual_prompt", "agent": "chat_agent"},
            {"step": "synthesize_image", "agent": "image_agent"}
        ]
    
    if intent == "code":
        return [
            {"step": "architect_logic", "agent": "chat_agent"},
            {"step": "generate_code", "agent": "code_agent"}
        ]

    if intent == "search":
        return [
            {"step": "gather_information", "agent": "search_agent"},
            {"step": "synthesize_results", "agent": "chat_agent"}
        ]

    # Multi-step/Complex Planning
    system_prompt = (
        "You are the LEVI Task Planner. Define a JSON array of steps for the task. "
        "Available agents: 'chat_agent', 'image_agent', 'search_agent', 'code_agent'. "
        "Each step MUST have: 'step' (descriptive name) and 'agent'. "
        "Output ONLY a valid JSON array."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task: {user_input}\nIntent: {intent}\nComplexity: {complexity}"}
    ]
    
    plan_raw = await call_lightweight_llm(messages)
    return _parse_json_result(plan_raw, [{"step": "fallback_chat", "agent": "chat_agent"}])


