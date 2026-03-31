"""
backend/services/orchestrator/brain.py

The "Brain" of LEVI AI. 
A structured orchestrator that routes user inputs based on intent, 
memory context, and available tools.
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator

from .planner import detect_intent, generate_plan
from .executor import execute_plan
from .memory_manager import MemoryManager
from .orchestrator_types import IntentResult, EngineRoute, OrchestratorResponse
from .local_engine import handle_local, is_locally_handleable
from backend.utils.robustness import standard_retry, TimeoutHandler

logger = logging.getLogger(__name__)

class LeviBrain:
    """
    Central AI Orchestrator: The brain of LEVI.
    Handles routing, intent detection, and multi-engine execution.
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.timeout = TimeoutHandler()

    async def route(self, user_input: str, user_id: str, session_id: str, streaming: bool = False, **kwargs) -> Any:
        """
        The main entry point for routing logic.
        Detects intent, fetches context, and delegates to specific engines.
        """
        request_id = f"orch_{uuid.uuid4().hex[:8]}"
        logger.info("[%s] Routing input: %s", request_id, user_input[:50])

        # 1. Fetch Context & Detect Intent in Parallel
        context_task = self.memory.get_combined_context(user_id, session_id, user_input)
        intent_task = detect_intent(user_input)
        
        context, intent = await asyncio.gather(context_task, intent_task)
        context.update(kwargs) # Add extra params like mood, tier

        # 2. Decision Logic
        intent_name = intent.intent
        complexity = intent.complexity
        
        logger.info("[%s] Intent: %s (Confidence: %.2f)", request_id, intent_name, intent.confidence)

        # 3. Route to specialized engines
        if is_locally_handleable(intent_name, complexity):
            return await self.local_engine(user_input, context, request_id)
        
        if intent_name == "code":
            return await self.code_engine(user_input, context, request_id)
            
        if intent_name == "tool_request" or intent_name in ("image", "search"):
            return await self.agent_engine(user_input, intent, context, request_id)

        # Default to General Chat
        return await self.chat_engine(user_input, intent, context, request_id, streaming=streaming)

    async def chat_engine(self, user_input: str, intent: IntentResult, context: Dict[str, Any], request_id: str, streaming: bool = False) -> Any:
        """Handles general conversation using the primary LLM."""
        logger.info("[%s] Using Chat Engine (Streaming: %s)", request_id, streaming)
        
        # Generation logic
        from .engine import generate_plan, execute_plan, synthesize_response, _build_messages
        
        if streaming:
            # Phase 3: True Streaming integration
            from backend.generation import async_stream_llm_response, _get_random_persona, _build_dynamic_system_prompt
            
            persona = _get_random_persona(context.get("mood", "philosophical"))
            system_prompt = _build_dynamic_system_prompt(persona)
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
            
            # Return metadata + generator (expected by the API layer)
            return {
                "intent": intent.intent,
                "route": EngineRoute.API.value,
                "request_id": request_id,
                "stream": async_stream_llm_response(messages)
            }

        # Static Response Path
        plan = await generate_plan(user_input, intent, context)
        results = await execute_plan(plan, context)
        response = await synthesize_response(results, context)
        
        return {
            "response": response,
            "intent": intent.intent,
            "route": EngineRoute.API.value,
            "request_id": request_id
        }

    async def code_engine(self, user_input: str, context: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handles programming and technical tasks."""
        logger.info("[%s] Using Code Engine", request_id)
        # Dedicated code logic here
        from .agent_registry import call_agent
        result = await call_agent("code_agent", {**context, "input": user_input})
        
        return {
            "response": result.get("message", "I couldn't generate the code you requested."),
            "intent": "code",
            "route": EngineRoute.TOOL.value,
            "request_id": request_id
        }

    async def agent_engine(self, user_input: str, intent: IntentResult, context: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Orchestrates multiple agents for complex tool-based tasks."""
        logger.info("[%s] Using Agent Engine (Multi-Agent)", request_id)
        
        from .agent_registry import call_agent
        agent_name = f"{intent.intent}_agent"
        result = await call_agent(agent_name, {**context, "input": user_input})
        
        return {
            "response": result.get("message", "Task completed."),
            "intent": intent.intent,
            "route": EngineRoute.TOOL.value,
            "job_id": result.get("job_id"),
            "request_id": request_id
        }

    async def local_engine(self, user_input: str, context: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Fast-path for greetings and simple queries (zero API cost)."""
        logger.info("[%s] Using Local Engine", request_id)
        response = handle_local(user_input, context)
        
        return {
            "response": response,
            "intent": "greeting",
            "route": EngineRoute.LOCAL.value,
            "request_id": request_id
        }
