"""
backend/services/orchestrator/brain.py

The "Brain" of LEVI AI. 
Central Orchestrator v2.0 — Autonomous Reasoning & Execution.
"""

import logging
import uuid
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncGenerator, Union

from .planner import detect_intent, generate_plan
from .executor import execute_plan
from .memory_manager import MemoryManager
from .orchestrator_types import IntentResult, EngineRoute, OrchestratorResponse
from .local_engine import handle_local, is_locally_handleable
from backend.utils.robustness import standard_retry, TimeoutHandler
from backend.generation import async_stream_llm_response, _get_random_persona, _build_dynamic_system_prompt, _async_call_llm_api

logger = logging.getLogger(__name__)

class LeviBrain:
    """
    Central AI Orchestrator: The brain of LEVI.
    Handles routing, intent detection, and multi-agent execution.
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.timeout = TimeoutHandler()

    async def route(self, user_input: str, user_id: str, session_id: str, streaming: bool = False, **kwargs) -> Any:
        """
        The main entry point for routing logic.
        1. Sanitization
        2. Memory Retrieval
        3. Intent Detection
        4. Decision Logic (Routing)
        5. Execution (Planning/Agents/Stream)
        """
        request_id = f"orch_{uuid.uuid4().hex[:8]}"
        logger.info("[%s] Routing input: %s", request_id, user_input[:50])

        # 1. Fetch Context & Detect Intent in Parallel
        context_task = self.memory.get_combined_context(user_id, session_id, user_input)
        intent_task = detect_intent(user_input)
        
        context, intent = await asyncio.gather(context_task, intent_task)
        context.update(kwargs) # Add extra params like mood, tier, user_id
        context["user_id"] = user_id
        context["session_id"] = session_id
        context["request_id"] = request_id
        context["input"] = user_input

        # 2. Decision Logic
        intent_name = intent.intent
        complexity = intent.complexity
        user_tier = context.get("user_tier", "free")
        
        logger.info("[%s] Intent: %s (Complexity: %d, Confidence: %.2f)", request_id, intent_name, complexity, intent.confidence)

        # 3. Decision Engine — Route Selection
        # ── 🟢 LOCAL ────────────────────────────────────────────────────────────
        if is_locally_handleable(intent_name, complexity):
            return await self.local_engine(user_input, context, request_id)
        
        # ── 🟡 TOOL ─────────────────────────────────────────────────────────────
        if intent_name in ("image", "code", "search", "tool_request"):
            return await self.agent_engine(user_input, intent, context, request_id)

        # ── 🔴 API ──────────────────────────────────────────────────────────────
        # Select Model based on complexity and tier
        if user_tier in ("pro", "creator") or complexity >= 8:
            model = "llama-3.1-70b-versatile"
        else:
            model = "llama-3.1-8b-instant"
        
        context["model"] = model
        
        if streaming:
            return await self.stream_engine(user_input, intent, context, request_id)
        
        return await self.reasoning_engine(user_input, intent, context, request_id)

    async def stream_engine(self, user_input: str, intent: IntentResult, context: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handles token-by-token streaming for conversational responses."""
        logger.info("[%s] Using Stream Engine (Model: %s)", request_id, context.get("model"))
        
        persona = _get_random_persona(context.get("mood", "philosophical"))
        depth = len(context.get("history", []))
        
        system_prompt = _build_dynamic_system_prompt(
            persona, 
            user_memory=context.get("long_term"), 
            conversation_depth=depth
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for turn in context.get("history", [])[-3:]:
             messages.append({"role": "user", "content": turn.get("user", "")})
             messages.append({"role": "assistant", "content": turn.get("bot", "")})
        messages.append({"role": "user", "content": user_input})
        
        return {
            "intent": intent.intent,
            "route": EngineRoute.API.value,
            "request_id": request_id,
            "stream": async_stream_llm_response(messages, model=context.get("model", "llama-3.1-8b-instant"))
        }

    async def reasoning_engine(self, user_input: str, intent: IntentResult, context: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Performs multi-step reasoning and synthesis for complex non-streaming queries."""
        logger.info("[%s] Using Reasoning Engine (Multi-Step)", request_id)
        
        # 1. Generate Execution Plan
        plan = await generate_plan(user_input, intent, context)
        
        # 2. Execute Plan
        execution_results = await execute_plan(plan, context)
        
        # 3. Synthesize Final Response
        from .engine import synthesize_response # Avoid circular import if possible, but engine.py has help utilities
        response = await synthesize_response(execution_results, context)
        
        # 4. Background Memory Storage (if not handled by gateway)
        # Gateway handles background tasks usually, but we ensure it's tracked here
        
        return {
            "response": response,
            "intent": intent.intent,
            "route": EngineRoute.API.value,
            "request_id": request_id,
            "plan": plan
        }

    async def agent_engine(self, user_input: str, intent: IntentResult, context: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Directly invokes a specialized agent for tool-based tasks."""
        logger.info("[%s] Using Agent Engine (Direct)", request_id)
        
        from .agent_registry import call_agent
        agent_name = f"{intent.intent}_agent"
        if intent.intent == "tool_request":
            agent_name = "chat_agent" # Fallback for generic tool requests
            
        result = await call_agent(agent_name, {**context, "input": user_input})
        
        return {
            "response": result.get("message", "Task completed."),
            "intent": intent.intent,
            "route": EngineRoute.TOOL.value,
            "job_id": result.get("job_id"),
            "request_id": request_id,
            "agent": agent_name
        }

    async def local_engine(self, user_input: str, context: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Fast-path for zero-latency, zero-cost interactions."""
        logger.info("[%s] Using Local Engine", request_id)
        response = handle_local(user_input, context)
        
        return {
            "response": response,
            "intent": "greeting",
            "route": EngineRoute.LOCAL.value,
            "request_id": request_id
        }
