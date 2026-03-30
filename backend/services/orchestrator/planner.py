import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

async def call_lightweight_llm(messages: List[Dict[str, str]], temperature: float = 0.5) -> Optional[str]:
    """Uses a lightweight model (llama-3.1-8b) for quick decisions."""
    from backend.generation import _async_call_llm_api
    return await _async_call_llm_api(
        messages=messages,
        temperature=temperature,
        max_tokens=200,
        model="llama-3.1-8b-instant",
        provider="groq"
    )

async def classify_intent(user_input: str) -> Dict[str, Any]:
    """Classify the user intent and assess task complexity."""
    system_prompt = (
        "You are the LEVI Intent Classifier. Categorize the user's input into: "
        "'chat', 'generate_image', 'research', 'task_execution', 'multi_step'. "
        "Also assess complexity from 1-10. "
        "Output ONLY JSON: {\"intent\": \"category\", \"complexity\": 5}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    res_json = await call_lightweight_llm(messages)
    if not res_json:
        return {"intent": "chat", "complexity": 1}
    
    try:
        if "```json" in res_json:
            res_json = res_json.split("```json")[1].split("```")[0]
        return json.loads(res_json.strip())
    except Exception:
        return {"intent": "chat" if "chat" in res_json.lower() else "multi_step", "complexity": 5}

async def generate_plan(user_input: str, intent_data: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate a step-by-step plan based on intent and complexity."""
    intent = intent_data.get("intent", "chat")
    complexity = intent_data.get("complexity", 1)

    if intent == "chat" and complexity < 4:
        return [{"step": "chat_response", "agent": "chat_agent"}]
    
    # For complex or specific tasks, use structured planning
    system_prompt = (
        "You are the LEVI Task Planner. Define a JSON array of steps. "
        "Available agents: 'chat_agent', 'image_agent', 'research_agent'. "
        f"Complexity Level: {complexity}/10. Use more specialized steps for higher complexity."
        "Output ONLY valid JSON array of objects with 'step' and 'agent'."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task: {user_input}"}
    ]
    
    plan_json = await call_lightweight_llm(messages)
    # ... (rest of the parsing logic same as before)
    
    if intent == "generate_image":
        return [
            {"step": "refine_prompt", "agent": "chat_agent"},
            {"step": "generate", "agent": "image_agent"}
        ]
    
    if intent == "research":
        return [
            {"step": "search", "agent": "research_agent"},
            {"step": "summarize", "agent": "chat_agent"}
        ]
    
    # For multi-step, use the LLM to generate the sequences
    system_prompt = (
        "You are the LEVI Task Planner. Define a JSON array of steps for the given task. "
        "Each step MUST have: 'step' (name) and 'agent' (which agent to use). "
        "Available agents: 'chat_agent', 'image_agent', 'research_agent'. "
        "Example Input: 'research AI trends and generate an image' "
        "Example JSON Output: ["
        "  {\"step\": \"search_trends\", \"agent\": \"research_agent\"}, "
        "  {\"step\": \"summarize_and_prompt\", \"agent\": \"chat_agent\"}, "
        "  {\"step\": \"create_art\", \"agent\": \"image_agent\"}"
        "]"
        "Output ONLY valid JSON."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task: {user_input}"}
    ]
    
    plan_json = await call_lightweight_llm(messages)
    if not plan_json:
        return [{"step": "fallback_chat", "agent": "chat_agent"}]
    
    try:
        # Clean up possible markdown fences
        if "```json" in plan_json:
            plan_json = plan_json.split("```json")[1].split("```")[0]
        elif "```" in plan_json:
            plan_json = plan_json.split("```")[1].split("```")[0]
        
        return json.loads(plan_json.strip())
    except Exception as e:
        logger.error(f"Failed to parse plan JSON: {e}")
        return [{"step": "error_fallback", "agent": "chat_agent"}]
