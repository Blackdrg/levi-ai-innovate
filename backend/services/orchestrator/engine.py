import logging
from typing import Dict, Any, Optional

from .planner import classify_intent, generate_plan
from .executor import execute_plan
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)

async def run_orchestrator(
    user_input: str,
    session_id: str,
    user_id: str,
    user_tier: str = "free",
    mood: str = "philosophical"
) -> str:
    """The main entry point for AI Orchestration."""
    logger.info(f"Orchestrating input: {user_input[:50]}... (Session: {session_id}, Tier: {user_tier})")
    
    # 1. Fetch Context (3-Layer Memory)
    context = await MemoryManager.get_combined_context(user_id, session_id)
    context.update({
        "input": user_input,
        "session_id": session_id,
        "user_id": user_id,
        "user_tier": user_tier,
        "mood": mood
    })
    
    # 2. Intent Detection
    intent = await classify_intent(user_input)
    logger.info(f"Detected intent: {intent}")
    context["intent"] = intent
    
    # 3. Planning
    plan = await generate_plan(user_input, intent, context)
    logger.info(f"Generated plan: {plan}")
    context["plan"] = plan
    
    # 4. Execution
    execution_results = await execute_plan(plan, context)
    
    # 5. Synthesis (Final Response Generation)
    final_response = await synthesize_response(execution_results, context)
    
    # 6. Memory Update
    MemoryManager.store_memory(user_id, session_id, user_input, final_response)
    
    return final_response

async def synthesize_response(results: list, context: Dict[str, Any]) -> str:
    """Combines individual agent outputs into a final coherent message."""
    if not results:
        return "I'm sorry, my thoughts were momentarily scattered. Please rephrase."
    
    # If it's a simple chat, just return the chat message
    if context.get("intent") == "chat" or len(results) == 1:
        # Check if the result was a chat response
        for item in results:
            res_msg = item.get("result", {}).get("message")
            if res_msg: return res_msg
        
        # Fallback to general chat if no message was found
        from backend.generation import generate_response
        return await generate_response(
            context.get("input", ""), 
            history=context.get("history", []),
            mood=context.get("mood", "philosophical"),
            user_tier=context.get("user_tier", "free")
        )
    
    # For multi-step, synthesize based on all results
    combined_content = ""
    for item in results:
        res = item.get("result", {})
        msg = res.get("message")
        if msg:
            combined_content += f"{msg}\n"
    
    # Final 'polish' call (optional synthesize persona)
    # Using the last message as the primary response if multiple were produced
    return combined_content.strip() or "Task complete. What should we explore next?"
