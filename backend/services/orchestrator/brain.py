"""
backend/services/orchestrator/brain.py

Central Orchestrator v3.0 — The Unified Deterministic Pipeline.
Enforces the flow: Intent Detect → Planning → Execution → Synthesis.
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator

from .planner import detect_intent, generate_plan
from .executor import execute_plan
from .memory_manager import MemoryManager
from .orchestrator_types import IntentResult, EngineRoute, OrchestratorResponse, ToolResult
from backend.utils.robustness import standard_retry, TimeoutHandler
from backend.generation import async_stream_llm_response, _build_dynamic_system_prompt
from backend.learning import AdaptivePromptManager, collect_training_sample

logger = logging.getLogger(__name__)

class LeviBrain:
    """
    The unified AI brain of LEVI.
    All requests, regardless of complexity, follow the same deterministic pipeline.
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.prompts = AdaptivePromptManager()

    async def route(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        streaming: bool = False, 
        request_id: Optional[str] = None,
        status_callback: Optional[callable] = None,
        **kwargs
    ) -> Any:
        """
        The main pipeline entry point.
        """
        request_id = request_id or f"orch_{uuid.uuid4().hex[:8]}"
        logger.info("Core Pipeline Entry: %s", user_input[:50])

        async def _notify(msg: str):
            if status_callback:
                if asyncio.iscoroutinefunction(status_callback):
                    await status_callback(msg)
                else:
                    status_callback(msg)

        # 1. Parallel Context & Intent Retrieval
        await _notify("Analyzing atmospheric intent...")
        context_task = self.memory.get_combined_context(user_id, session_id, user_input)
        intent_task = detect_intent(user_input)
        
        context, intent = await asyncio.gather(context_task, intent_task)
        
        # Enrich context
        context.update(kwargs)
        context.update({
            "user_id": user_id,
            "session_id": session_id,
            "request_id": request_id,
            "input": user_input,
            "intent": intent.intent,
            "complexity": intent.complexity,
            "status_callback": status_callback # Propagate to executor
        })

        # 2. Meta-Brain Planning (Phase 1 Evolution)
        from .meta_planner import decompose_goal, map_strategy_to_plan
        
        await _notify(f"Meta-Brain: Decomposing {intent.intent} goal...")
        strategy = await decompose_goal(user_input, intent, context)
        
        # Stream the high-level strategy to the user for transparency
        await _notify(f"Strategy: {strategy.overall_strategy}")
        
        plan = map_strategy_to_plan(strategy, intent)
        logger.info("Meta-Plan Generated: %s (%d steps)", strategy.overall_strategy[:30], len(plan.steps))

        # ── 🟢 Local Path Short-Circuit (Optimization: Tier 1) ─────────────────
        # If the plan only has local_agent and we're not streaming, return fast.
        # This saves costs by using $0 internal logic before hitting any External APIs.
        if len(plan.steps) == 1 and plan.steps[0].agent == "local_agent" and not streaming:
            from .tool_registry import call_tool
            res = await call_tool("local_agent", {"input": user_input, "mood": context.get("mood")}, context)
            return {
                "response": res.get("message"),
                "intent": intent.intent,
                "route": EngineRoute.LOCAL.value,
                "request_id": request_id
            }

        # ── 🔴 Streaming Path (Tier 2 & 3) ───────────────────────────────────
        if streaming and intent.intent in ("chat", "greeting", "simple_query"):
            return await self._stream_pipeline(user_input, intent, context, request_id)

        # 3. Execution (Phase 2)
        execution_results = await execute_plan(plan, context)
        
        # 4. Synthesis (Phase 3)
        from .engine import synthesize_response
        response = await synthesize_response(execution_results, context)

        # ── LEVI v6: Stage 5 — Optimization Pass (The Soul) ──────────────────
        # Optimization elevates the final response to ensure philosophical resonance.
        user_tier = context.get("user_tier", "free")
        should_optimize = False
        
        if user_tier in ("pro", "creator"):
            should_optimize = True
        else:
            # Free-tier: 5% chance optimization + Daily Rate Limit check
            import random
            if random.random() < 0.05:
                from backend.redis_client import HAS_REDIS, r as redis_client
                if HAS_REDIS:
                    daily_key = f"limit:opt:{user_id}:{datetime.now().strftime('%Y%m%d')}"
                    usage = int(redis_client.get(daily_key) or 0)
                    if usage < 3: # Limit free optimization to 3 per day
                        should_optimize = True
                        redis_client.incr(daily_key)
                        redis_client.expire(daily_key, 86400)

        if should_optimize and intent.complexity >= 4:
            await _notify("Elevating response resonance...")
            from .tool_registry import call_tool
            opt_raw = await call_tool("optimizer_agent", {
                "original_input": user_input,
                "draft_response": response,
                "user_context": context
            }, context)
            
            if opt_raw.get("success"):
                response = opt_raw.get("data", {}).get("optimized_content", response)
                logger.info("Optimization Pass Completed.")

        # 6. Background Tasks (Memory Storage / Learning)
        self._trigger_background_tasks(user_input, response, context)

        # Construct final payload
        return {
            "response": response,
            "intent": intent.intent,
            "route": EngineRoute.API.value if intent.complexity > 3 else EngineRoute.LOCAL.value,
            "request_id": request_id,
            "plan": plan.dict(),
            "results": [r.dict() for r in execution_results]
        }

    async def _stream_pipeline(
        self, 
        user_input: str, 
        intent: IntentResult, 
        context: Dict[str, Any], 
        request_id: str
    ) -> Dict[str, Any]:
        """Handles the token-by-token streaming version of the pipeline."""
        logger.info("Entering Stream Pipeline")
        
        # For streaming, we currently only support 1-step conversational flow.
        # If the intent requires more, it will be handled by the non-streaming reasoning engine.
        
        mood = context.get("mood", "philosophical")
        base_variant = await self.prompts.get_best_variant(mood)
        
        depth = len(context.get("history", []))
        system_prompt = _build_dynamic_system_prompt(
            base_variant, 
            user_memory=context.get("long_term"), 
            conversation_depth=depth,
            preferences=context.get("preferences")
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for turn in context.get("history", [])[-3:]:
             messages.append({"role": "user", "content": turn.get("user", "")})
             messages.append({"role": "assistant", "content": turn.get("bot", "")})
        messages.append({"role": "user", "content": user_input})
        
        # 3. Hybrid Model Selection (Cost-Optimized)
        # Tier 2: 8B for most users / simple intents
        # Tier 3: 70B for Pro/Creator or Complex reasoning
        user_tier = context.get("user_tier", "free")
        if user_tier in ("pro", "creator") or intent.complexity >= 8:
            model = "llama-3.1-70b-versatile"
        else:
            model = "llama-3.1-8b-instant"
        
        logger.info("Routing to %s (Tier %d)", model, 3 if "70b" in model else 2)
        
        return {
            "intent": intent.intent,
            "route": EngineRoute.API.value,
            "request_id": request_id,
            "stream": async_stream_llm_response(messages, model=model)
        }

    def _trigger_background_tasks(self, user_input: str, response: str, context: Dict[str, Any]):
        """Schedules non-blocking memory and learning updates."""
        user_id = context.get("user_id")
        session_id = context.get("session_id")
        user_tier = context.get("user_tier", "free")
        
        if user_id and not str(user_id).startswith("guest:"):
            # 1. Standard Memory Updates
            asyncio.create_task(self.memory.store_memory(user_id, session_id, user_input, response))
            asyncio.create_task(self.memory.process_new_interaction(user_id, user_input, response))
            
            # 2. Personalized Learning Feedback
            asyncio.create_task(collect_training_sample(
                user_message=user_input,
                bot_response=response,
                mood=context.get("mood", "philosophical"),
                session_id=session_id,
                user_id=user_id
            ))

            # 3. LEVI v6: Shared Pattern Learning (Anonymized)
            # If any execution result was a failure, we log it to a global 'failure' pool 
            # for system-level Meta-Brain fine-tuning.
            results = context.get("execution_history", [])
            for res in results:
                if not res.success:
                    asyncio.create_task(self._log_anonymized_failure(res, user_tier))

            # 4. LEVI v6 Phase 3: Global Evolution Triggers
            from backend.redis_client import HAS_REDIS
            if HAS_REDIS:
                from backend.redis_client import r as redis_client
                # a) Shared Pattern Learning (Only absolute best)
                # Note: rating is assumed to be handled in process_new_interaction background task
                # but we'll trigger the global pattern collector here if it's high quality
                if context.get("rating", 0) >= 5:
                    from backend.learning import collect_global_pattern
                    asyncio.create_task(collect_global_pattern(user_input, response, 5))

                # b) Autonomous Prompt Mutation (Weekly/Milestone trigger)
                evolve_key = "system:evolution:interaction_count"
                count = redis_client.incr(evolve_key)
                if count >= 100: # Every 100 interactions system-wide, consider mutation
                    logger.info("[Brain] Threshold reached. Triggering autonomous prompt evolution...")
                    asyncio.create_task(self.prompts.evolve_variants())
                    redis_client.set(evolve_key, 0)

    async def _log_anonymized_failure(self, result: Any, tier: str):
        """
        Logs a stripped, non-PII execution failure to Redis for pattern analysis.
        """
        from backend.redis_client import HAS_REDIS, r as redis_client
        if HAS_REDIS:
            pattern_key = f"learning:failures:{result.agent}"
            error_data = {
                "error": (result.error or "Unknown").split(":")[0][:50],
                "tier": tier,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            # We use a Redis List as a temporary buffer for anonymized patterns
            redis_client.lpush("patterns:shared:failures", json.dumps(error_data))
            redis_client.ltrim("patterns:shared:failures", 0, 999) # Keep last 1000
