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
from .orchestrator_types import IntentResult, EngineRoute, OrchestratorResponse, ToolResult, DecisionLog
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

        # 1. Exact Match Cache Check (Step 1)
        from backend.redis_client import check_exact_match, store_exact_match
        cached_res = check_exact_match(user_id, user_input, kwargs.get("mood", "philosophical"))
        if cached_res:
             logger.info("[Brain] Exact Match Cache Hit.")
             return {
                 "response": cached_res,
                 "intent": "cached",
                 "route": "cache",
                 "request_id": request_id
             }
        
        # 1.1 Semantic Cache Check (LEVI v6 Phase 12)
        from backend.redis_client import check_semantic_match, store_semantic_match
        semantic_res = check_semantic_match(user_id, user_input, kwargs.get("mood", "philosophical"), threshold=0.92)
        if semantic_res:
             logger.info("[Brain] Semantic Cache Hit (Similarity > 0.92)")
             return {
                 "response": semantic_res,
                 "intent": "cached_semantic",
                 "route": "cache",
                 "request_id": request_id
             }

        # 2. Context Builder & Memory Injection (Step 2 & 3)
        await _notify("Hydrating atmospheric context...")
        context = await self.memory.get_combined_context(user_id, session_id, user_input)
        context.update(kwargs) # user_tier, mood, etc.

        # 2.5 Brain-Controlled Context Injection (BCCI - Phase 17)
        # 1. Allocate Token Budget
        from .context_utils import allocate_budget
        user_tier = kwargs.get("user_tier", "free")
        budget = allocate_budget(intent.intent_type, user_tier, intent.complexity_level)
        context["budget"] = budget
        
        # 2. Dynamic Few-Shot (ICL) Selection
        # Only inject if complexity >= 2 or confidence < 0.85
        from backend.learning import retrieve_resonant_patterns
        if intent.complexity_level >= 2 or intent.confidence_score < 0.85:
            patterns = await retrieve_resonant_patterns(user_input)
            context["few_shot_patterns"] = patterns
            if patterns:
                 logger.info("[Brain] BCCI: %d successful patterns retrieved.", len(patterns))
        else:
            context["few_shot_patterns"] = []
            logger.info("[Brain] BCCI: Zero-Pattern path selected for simple intent.")
        
        # 3. Intent Classification (Step 4)
        await _notify("Analyzing intent complexity...")
        intent = await detect_intent(user_input)
        
        # 4. 🔥 Decision Engine (NEW - Step 5)
        decision = DecisionLog(
            request_id=request_id,
            user_id=user_id,
            intent_type=intent.intent_type,
            complexity_level=intent.complexity_level,
            confidence_score=intent.confidence_score,
            estimated_cost_weight=intent.estimated_cost_weight,
            route=EngineRoute.LOCAL if intent.complexity_level <= 1 else EngineRoute.API
        )
        logger.info("[DecisionEngine] Path Selected: Level %d (%s)", decision.complexity_level, decision.intent_type)
        
        # 5. Engine Selector & Execution (Step 6)
        # ── 🟢 Level 0: Trivial (Short-Circuit) ──
        if decision.complexity_level == 0:
            await _notify("Executing zero-engine fast path...")
            from .tool_registry import call_tool
            res = await call_tool("local_agent", {"input": user_input, "mood": context.get("mood")}, context)
            response = res.get("message", "Greetings.")
            # Store in exact match cache for next time
            store_exact_match(user_id, user_input, context.get("mood", "philosophical"), response)
            return {
                "response": response,
                "intent": intent.intent_type,
                "route": EngineRoute.LOCAL.value,
                "request_id": request_id,
                "decision": decision.as_dict()
            }

        # ── 🟡 Level 1: Simple (Single cheap engine) ──
        if decision.complexity_level == 1 and not streaming:
            await _notify("Routing to single-engine path...")
            from .tool_registry import call_tool
            res = await call_tool("local_agent", {"input": user_input}, context)
            return {
                "response": res.get("message"),
                "intent": intent.intent_type,
                "route": EngineRoute.LOCAL.value,
                "request_id": request_id,
                "decision": decision.as_dict()
            }

        # ── 🔴 Streaming Path (Handled separately) ──
        if streaming and decision.complexity_level <= 2:
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

        # 9. Persistent Logging (Step 8)
        asyncio.create_task(self._log_decision_path(decision))

        # Construct final payload
        return {
            "response": response,
            "intent": intent.intent_type,
            "route": EngineRoute.API.value if intent.complexity_level > 1 else EngineRoute.LOCAL.value,
            "request_id": request_id,
            "plan": plan.dict(),
            "results": [r.dict() for r in execution_results],
            "decision": decision.as_dict()
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
            preferences=context.get("preferences"),
            few_shot_patterns=context.get("few_shot_patterns")
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for turn in context.get("history", [])[-3:]:
             messages.append({"role": "user", "content": turn.get("user", "")})
             messages.append({"role": "assistant", "content": turn.get("bot", "")})
        messages.append({"role": "user", "content": user_input})
        
        # 3. Hybrid Model Selection (Cost-Optimized)
        user_tier = context.get("user_tier", "free")
        if user_tier in ("pro", "creator") or intent.complexity_level == 3:
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
            rating = context.get("rating") or context.get("auto_rating", 3)
            asyncio.create_task(collect_training_sample(
                user_message=user_input,
                bot_response=response,
                mood=context.get("mood", "philosophical"),
                rating=rating,
                session_id=session_id,
                user_id=user_id
            ))

            # 3. LEVI v6 Phase 18: Learning Escalation Metrics
            from .learning_escalation import EscalationManager
            # We use an estimated quality score if no real rating yet
            EscalationManager.record_interaction_metrics(
                rating=rating,
                confidence=context.get("confidence_score", 0.9)
            )

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
                if count >= 25: 
                    from backend.redis_client import distributed_lock
                    with distributed_lock("prompt_evolution_mutex", ttl=30) as acquired:
                        if acquired:
                            logger.info("[Brain] Lock Acquired. Triggering autonomous prompt evolution...")
                            asyncio.create_task(self.prompts.evolve_variants())
                            redis_client.set(evolve_key, 0)
                        else:
                            logger.info("[Brain] Evolution locked by another instance. Skipping.")

    async def _log_decision_path(self, decision: DecisionLog):
        """
        Logs the adaptive decision path to Redis and Firestore.
        """
        from backend.redis_client import HAS_REDIS
        data = decision.as_dict()
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # 1. Redis for real-time monitoring
        if HAS_REDIS:
            from backend.redis_client import r as redis_client
            redis_client.lpush(f"audit:decisions:{decision.user_id}", json.dumps(data))
            redis_client.ltrim(f"audit:decisions:{decision.user_id}", 0, 99) # Keep 100
            
            # --- Global Dashboard Stats ---
            redis_client.incr(f"stats:route:{decision.route.value}")
            redis_client.incr(f"stats:complexity:{decision.complexity_level}")
            
            # Moving average for cost
            prev_avg = float(redis_client.get("stats:avg_cost_weight") or 0.0)
            new_avg = (prev_avg * 0.95) + (decision.estimated_cost_weight * 0.05)
            redis_client.set("stats:avg_cost_weight", str(new_avg))
            
        # 2. Firestore for persistent history
        try:
            from backend.firestore_db import db as firestore_db
            firestore_db.collection("decision_audit").document(decision.request_id).set(data)
        except Exception as e:
            logger.error(f"Decision logging failed: {e}")

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
