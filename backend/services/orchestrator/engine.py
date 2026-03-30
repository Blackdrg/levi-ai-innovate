import logging
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks

from .planner import classify_intent, generate_plan
from .executor import execute_plan
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)

async def run_orchestrator(
    user_input: str,
    session_id: str,
    user_id: str,
    background_tasks: Optional[BackgroundTasks] = None,
    user_tier: str = "free",
    mood: str = "philosophical"
) -> str:
    """The main entry point for AI Orchestration with Phase 3 Upgrades."""
    logger.info(f"Orchestrating input: {user_input[:50]}... (Session: {session_id}, Tier: {user_tier})")
    
    # 1. Fetch Context (3-Layer Memory + Semantic search based on query)
    context = await MemoryManager.get_combined_context(user_id, session_id, query=user_input)
    context.update({
        "input": user_input,
        "session_id": session_id,
        "user_id": user_id,
        "user_tier": user_tier,
        "mood": mood
    })
    
    # 2. Intent Detection & Model Routing (Phase 3)
    intent = await classify_intent(user_input)
    logger.info(f"Detected intent: {intent}")
    context["intent"] = intent
    
    # 3. Planning
    plan = await generate_plan(user_input, intent, context)
    logger.info(f"Generated plan: {plan}")
    context["plan"] = plan
    
    # 4. Execution (with Self-Healing)
    execution_results = await execute_plan(plan, context)
    
    # 5. Synthesis (Advanced Conductor Synthesis)
    final_response = await synthesize_response(execution_results, context)
    
    # 6. Memory Update
    # Short-term (Sync)
    MemoryManager.store_memory(user_id, session_id, user_input, final_response)
    
    # Long-term Fact Extraction (Async Background Task - Phase 3)
    if background_tasks:
        background_tasks.add_task(
            MemoryManager.process_new_interaction, 
            user_id, user_input, final_response
        )
    else:
        # Fallback to sync or fire-and-forget if no background_tasks provided
        asyncio.create_task(MemoryManager.process_new_interaction(user_id, user_input, final_response))
    
    return final_response

async def synthesize_response(results: list, context: Dict[str, Any]) -> str:
    """Advanced Synthesis: Uses an LLM to merge agent outputs into LEVI's persona."""
    if not results:
        return "I'm sorry, my thoughts were momentarily scattered. Please rephrase."
    
    # Simple single-step chat follows standard path for performance
    if context.get("intent") == "chat" and len(results) == 1:
        msg = results[0].get("result", {}).get("message")
        if msg: return msg

    # Complex/Multi-step synthesis
    from backend.generation import _async_call_llm_api
    
    agent_outputs = "\n---\n".join([
        f"Agent: {r['agent']}\nStep: {r['step']}\nOutput: {r.get('result', {}).get('message', r.get('error'))}"
        for r in results
    ])
    
    synth_prompt = (
        f"You are LEVI, a {context.get('mood', 'philosophical')} AI. "
        "I will provide you with outputs from several specialized agents regarding a user task. "
        "Your job is to synthesize these into a single, cohesive, elegant response in YOUR VOICE. "
        "Do not list the steps. Do not say 'Agent X said'. "
        "Speak directly and deeply. Mention user preferences if they appear in context. "
        f"\nUser Preferences: {context.get('long_term', {}).get('relevant_facts', [])}"
        f"\nUser Task: {context.get('input')}"
        f"\nAgent Results:\n{agent_outputs}"
    )

    # Use a stronger model for synthesis if user is high-tier
    model = "llama-3.1-70b-versatile" if context.get("user_tier") in ["pro", "creator"] else "llama-3.1-8b-instant"
    
    synthesized = await _async_call_llm_api(
        messages=[{"role": "system", "content": synth_prompt}],
        model=model,
        temperature=0.7
    )

    return synthesized or results[-1].get("result", {}).get("message", "Task complete.")

import asyncio
