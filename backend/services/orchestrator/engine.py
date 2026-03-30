import logging
import asyncio
import uuid
import os
from typing import Dict, Any, Optional, List, Union

from .planner import detect_intent, generate_plan
from .executor import execute_plan
from .memory_manager import MemoryManager
from .orchestrator_types import IntentResult, OrchestratorResponse
from backend.config import TIERS, COST_MATRIX
from backend.auth import check_allowance

logger = logging.getLogger(__name__)

async def run_orchestrator(
    user_input: str,
    session_id: str,
    user_id: str = "guest",
    background_tasks: Any = None,
    user_tier: str = "free",
    mood: str = "philosophical"
) -> Dict[str, Any]:
    """The central entry point for all LEVI AI interactions."""
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    logger.info(f"[{request_id}] Orchestrator started for user {user_id} (Tier: {user_tier})")
    
    job_ids = []
    intent_name = "chat"

    # 0. Phase 4: Allowance Check
    if user_id and not user_id.startswith("guest:"):
        if not check_allowance(user_id, user_tier, cost=COST_MATRIX["chat"]):
            return {
                "response": "Your daily AI allowance has been reached. Please upgrade or wait until tomorrow to continue our journey.",
                "intent": "system",
                "session_id": session_id,
                "job_ids": []
            }

    try:
        # 1. Retrieve Context
        context = await MemoryManager.get_combined_context(user_id, session_id, user_input)
        context["user_tier"] = user_tier
        context["mood"] = mood

        # 2. Intent Analysis
        intent = await detect_intent(user_input)
        intent_name = intent.intent

        # 3. Decision Engine
        engine_config = await decide_engine(intent, context)

        # 4. Multi-Agent Routing
        if intent.intent in ["image", "code", "search"] and intent.confidence > 0.6:
            from .agent_registry import call_agent
            agent_result = await call_agent(f"{intent.intent}_agent", {
                "input": user_input,
                "context": context,
                "user_id": user_id,
                "user_tier": user_tier
            })
            bot_response = agent_result.get("message", "Tool execution failed.")
            if agent_result.get("job_id"):
                job_ids.append(agent_result["job_id"])
        else:
            # 5. Execution (Brain Synthesis)
            plan = await generate_plan(user_input, intent, context)
            execution_results = await execute_plan(plan, context)
            bot_response = await synthesize_response(execution_results, context)

        # 6. Post-Processing & Memory Update
        if background_tasks:
            background_tasks.add_task(MemoryManager.process_new_interaction, user_id, user_input, bot_response)
            background_tasks.add_task(MemoryManager.store_memory, user_id, session_id, user_input, bot_response)
        
        # Deduct cost
        if user_id and not user_id.startswith("guest:"):
            from backend.payments import use_credits
            use_credits(user_id, action=intent_name if intent_name in COST_MATRIX else "chat")

        return {
            "response": bot_response,
            "intent": intent_name,
            "session_id": session_id,
            "job_ids": job_ids,
            "request_id": request_id
        }

    except Exception as e:
        logger.exception(f"[{request_id}] Orchestrator failed: {e}")
        return {
            "response": "I apologize, but my internal circuits are experiencing a paradox. Let us try again.",
            "intent": "error",
            "session_id": session_id,
            "job_ids": []
        }


async def decide_engine(intent: IntentResult, context: Dict[str, Any]) -> Dict[str, Any]:
    """Decides which LLM engine / model to use based on tier and intent."""
    user_tier = context.get("user_tier", "free")
    # Free tier gets 8B for simple and 70B for high complexity (8+).
    
    if user_tier in ["pro", "creator"] or complexity >= 8:
        model = "llama-3.1-70b-versatile"
        provider = "groq"
    else:
        model = "llama-3.1-8b-instant"
        provider = "groq"
        
    # Internal Model logic (Future Phase: Local inference)
    use_internal = False
    if complexity <= 2 and intent.intent == "chat":
        # Check if local model service is healthy in production
        if os.getenv("USE_INTERNAL_MODEL") == "true":
            use_internal = True
        
    return {
        "model": model,
        "provider": provider,
        "use_internal": use_internal
    }

async def synthesize_response(results: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
    """Synthesizes agent outputs into the LEVI deep philosophical persona."""
    if not results:
        return "My internal pathways are clouded. Could you repeat that?"
    
    # If it was a simple single-step chat without need for complex synthesis
    if len(results) == 1 and results[0]["agent"] == "chat_agent" and not results[0].get("fallback"):
        msg = results[0].get("result", {}).get("message")
        if msg: return msg

    # Complex multi-step synthesis
    from backend.generation import _async_call_llm_api
    
    ltm = context.get("long_term", {})
    pulse = context.get("interaction_pulse", "stable")
    
    # Prepare Fact String from Memory
    fact_parts = []
    if ltm:
        if ltm.get("preferences"): fact_parts.append(f"User Preferences: {', '.join(ltm['preferences'])}")
        if ltm.get("traits"): fact_parts.append(f"User Traits: {', '.join(ltm['traits'])}")
        if ltm.get("history"): fact_parts.append(f"Relevant History: {', '.join(ltm['history'])}")
    
    fact_str = "\n".join(fact_parts)

    # Extract all agent outputs
    agent_outputs = []
    for r in results:
        agent_name = r["agent"]
        output = r.get("result", {}).get("message") or r.get("error", "Task failed.")
        agent_outputs.append(f"Agent [{agent_name}] output: {output}")
        
    outputs_str = "\n---\n".join(agent_outputs)
    
    synth_prompt = (
        f"Role: You are LEVI, a {context.get('mood', 'philosophical')} AI with a {pulse} pulse. "
        "Goal: Synthesize the agent outputs into a deeply personalized, cohesive response. "
        "Voice: Poetic, direct, and slightly detached yet observant. "
        "Constraints: Integrate context naturally. Do NOT mention specific agents by name. "
        "User Context:\n"
        f"{fact_str}\n\n"
        "Input Task: " + context.get("input", "") + "\n\n"
        "Agent Results:\n"
        f"{outputs_str}"
    )

    try:
        synthesized = await _async_call_llm_api(
            messages=[{"role": "system", "content": synth_prompt}],
            model=context["engine_config"]["model"],
            provider=context["engine_config"]["provider"],
            temperature=0.8
        )
        return synthesized or "Response synthesis failed. I am still processing."
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        return results[-1].get("result", {}).get("message") or "I encountered a barrier while synthesizing my thoughts."

