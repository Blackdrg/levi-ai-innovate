import logging
import uuid
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator

from .goal_engine import GoalEngine
from .planner import DAGPlanner
from .executor import GraphExecutor
from .critic import ReflectionEngine
from .learning import LearningLoopV8
from .decision_engine import DecisionEngine
from .llm_guard import LLMGuard
from .engines.deterministic_engine import DeterministicEngine
from .engines.code_engine import CodeEngine
from .engines.data_engine import DataEngine
from .engines.knowledge_engine import KnowledgeEngine
from .evolution_engine import EvolutionEngine
from .self_improvement import SelfImprovementLoop
from .handoff import NeuralHandoffManager
from backend.memory.manager import MemoryManager
from ..orchestrator_types import ToolResult, IntentResult
from backend.api.v8.telemetry import broadcast_mission_event

logger = logging.getLogger(__name__)

class LeviBrainCoreController:
    """
    LeviBrain Core Controller (v9.8.1)
    PRIMARY DIRECTIVE: Internal Engines & System Logic FIRST.
    Priority Stack:
    LEVEL 1: Internal Brain Logic / Memory
    LEVEL 2: Engine Execution (Deterministic)
    LEVEL 3: Agent Tool Usage
    LEVEL 4: LLM Fallback (Last Resort)
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.goal_engine = GoalEngine()
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reflection = ReflectionEngine()
        self.learning = LearningLoopV8()
        self.decision_engine = DecisionEngine()
        self.llm_guard = LLMGuard()
        self.handoff = NeuralHandoffManager()
        
        # Self-Correction State (v9.5)
        self.failure_buffer: List[Dict[str, Any]] = []
        
        # Engine Registry Initialization (v8.15)
        self.engine_registry = EngineRegistry()
        self.engine_registry.register("deterministic", DeterministicEngine())
        self.engine_registry.register("code", CodeEngine())
        self.engine_registry.register("data", DataEngine())
        self.engine_registry.register("knowledge", KnowledgeEngine())
        
        self.evolution_engine = EvolutionEngine()
        
        # Execution Metrics (v8.12)
        self.metrics_registry = {
            "tasks_solved_internal": 0,
            "tasks_solved_engine": 0,
            "tasks_solved_memory": 0,
            "tasks_solved_llm": 0
        }

    async def route(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Unified Cognitive Entry Point v9.8.1.
        Routes the mission to either the Batch or Streaming pipeline.
        """
        if streaming:
            return self.stream(user_input, user_id, session_id, **kwargs)
        else:
            return await self.run(user_input, user_id, session_id, **kwargs)

    async def run(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        request_id = f"v8_{uuid.uuid4().hex[:8]}"
        mission_start = datetime.now(timezone.utc)
        logger.info("[LeviBrain] Starting Cognitive Mission: %s", request_id)

        # 1. PERCEPTION & DECISION
        perception = await self._perceive(user_input, user_id, session_id, **kwargs)
        metrics = await self.decision_engine.compute_metrics(
            user_input, perception["intent"], self.memory, user_id, session_id
        )
        decision = self.decision_engine.decide(metrics)
        
        broadcast_mission_event(user_id, "perception", {
            "request_id": request_id, 
            "intent": str(perception["intent"]),
            "decision": decision,
            "metrics": metrics
        })
        
        results = []
        final_response = None

        # 1.5 ACTIVE MEMORY & EVOLUTION CHECK
        # If a promoted pattern exists, skip all processing
        evolution_match = self.evolution_engine.apply(user_input)
        if evolution_match:
            logger.info("[LeviBrain] Evolution match found. Skipping computation.")
            return {
                "response": evolution_match,
                "request_id": request_id,
                "decision": "EVOLUTION",
                "latency_ms": 0,
                "results": [],
                "metrics": self.metrics_registry
            }

        # Check memory confidence shortcut
        if metrics.get("memory_match_score", 0) > 0.75:
            logger.info("[LeviBrain] High-confidence memory match. Shortcut active.")
            final_response = await self._solve_internally(perception, metrics)
            return {
                "response": final_response,
                "request_id": request_id,
                "decision": "MEMORY_SHORTCUT",
                "latency_ms": 10,
                "results": [],
                "metrics": self.metrics_registry
            }
        if decision == "RULE" and metrics["has_rule"]:
            logger.info("[LeviBrain] Decision: RULE match (Deterministic Shortcut).")
            final_response = metrics["rule_data"]
            self.metrics_registry["tasks_solved_internal"] += 1
            execution_level = 1
            
        elif decision == "INTERNAL":
            logger.info("[LeviBrain] Decision: INTERNAL logic path.")
            final_response = await self._solve_internally(perception, metrics)
            self.metrics_registry["tasks_solved_internal"] += 1
            execution_level = 1
        
        elif decision == "ENGINE" and metrics["capable_engine"]:
            engine_name = metrics["capable_engine"]
            logger.info("[LeviBrain] Decision: ENGINE path -> %s", engine_name)
            
            # Execute via the new Engine Registry
            engine_res = await self.engine_registry.execute(engine_name, user_input)
            
            # Standardize internal result to ToolResult for consistency
            tool_res = ToolResult(
                success=engine_res.get("success", False),
                message=engine_res.get("message", str(engine_res.get("data", ""))),
                data=engine_res.get("data"),
                agent=engine_name
            )
            results.append(tool_res)
            final_response = tool_res.message
            
            # Metrics Tracking (Step 7)
            self.metrics_registry["tasks_solved_engine"] += 1
            execution_level = 2
            
        elif decision == "MEMORY" and metrics["memory_match_score"] > 0.75:
            logger.info("[LeviBrain] Decision: MEMORY shortcut (Skipping Plan).")
            final_response = await self._solve_internally(perception, metrics)
            self.metrics_registry["tasks_solved_memory"] += 1
            execution_level = 1
            
        else:
            # 3. NEURAL FALLBACK (LLM/DAG)
            logger.info("[LeviBrain] Decision: LLM/NEURAL fallback.")
            
            # v9.5 Neural Handoff: Local vs Cloud
            handoff_request = await self.handoff.route_inference(user_input, perception["context"])
            if handoff_request.get("target") == "local":
                 logger.info(f"[NeuralHandoff] Active. Routing to LOCAL ({handoff_request['provider']})...")
                 # We mark the request as local for the synthesis pass
                 perception["context"]["local_handoff"] = True
                 perception["context"]["handoff_provider"] = handoff_request["provider"]
            
            # Check LLM Guard before proceeding
            if not self.llm_guard.allow_llm(user_input, metrics):
                return {"response": "LLM access restricted by Brain Policy. deterministic path required.", "request_id": request_id}

            # GOAL & PLANNING
            goal = await self.goal_engine.create_goal(perception)
            broadcast_mission_event(user_id, "goal", {"request_id": request_id, "objective": goal.objective})

            # PLANNING (DAG) - Check for shortcuts
            task_graph = await self.planner.build_task_graph(goal, perception)
            broadcast_mission_event(user_id, "planning", {"request_id": request_id, "graph": task_graph.to_dict()})
            
            # EXECUTION (v9.8.1: Dynamic Concurrency)
            concurrency = await self._get_concurrency_limit(user_id)
            results = await self.executor.run(task_graph, perception, concurrency_limit=concurrency)
            broadcast_mission_event(user_id, "execution", {"request_id": request_id, "results_count": len(results), "concurrency": concurrency})

            # 4. FINAL BRAIN SYNTHESIS
            # In v8.12, the Brain synthesizes the structured data from agents
            final_response = await self._brain_synthesis(results, goal, perception)
            self.metrics_registry["tasks_solved_llm"] += 1
            execution_level = 4

        # 6. MEMORY UPDATE & LEARNING
        await self._update_memory(user_input, final_response, perception, results, execution_level)

        # 7. RESPONSE SYNCHRONIZATION
        latency = (datetime.now(timezone.utc) - mission_start).total_seconds() * 1000
        return {
            "response": final_response,
            "request_id": request_id,
            "decision": decision,
            "latency_ms": latency,
            "results": [r.dict() if hasattr(r, "dict") else r for r in results],
            "metrics": self.metrics_registry
        }

    async def stream(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        High-Fidelity SSE Streaming Pass (v9.8.1).
        Architecture: Metadata -> Perception -> Activity -> Execution -> Token Stream.
        """
        request_id = f"v9_stream_{uuid.uuid4().hex[:8]}"
        logger.info("[V9 Brain] Starting Streaming Mission: %s", request_id)

        yield {"event": "metadata", "data": {"request_id": request_id, "status": "pulsing"}}

        # 1. PERCEPTION & DECISION
        perception = await self._perceive(user_input, user_id, session_id, **kwargs)
        metrics = await self.decision_engine.compute_metrics(
            user_input, perception["intent"], self.memory, user_id, session_id
        )
        decision = self.decision_engine.decide(metrics)
        
        yield {"event": "perception", "data": {
            "request_id": request_id, 
            "intent": perception["intent"].intent_type.upper(),
            "decision": decision,
            "metrics": metrics
        }}

        # Evolution Shortcut
        evo_match = self.evolution_engine.apply(user_input)
        if evo_match:
            yield {"event": "activity", "data": "Evolution Pattern Match. Returning cached solution..."}
            yield {"event": "neural_synthesis", "data": {"token": evo_match, "done": True}}
            return

        try:
            if decision == "RULE" and metrics["has_rule"]:
                # v8.14: Perfect Determinism (Rule Hit)
                yield {"event": "activity", "data": "Deterministic Rule Hit. Returning solution..."}
                final_response = metrics["rule_data"]
                yield {"event": "neural_synthesis", "data": {"token": final_response, "done": True}}
                asyncio.create_task(self._update_memory(user_input, final_response, perception, [], 1))
                
            elif decision == "INTERNAL":
                # LEVEL 1: INTERNAL BRAIN LOGIC
                yield {"event": "activity", "data": "Processing via Internal Logic..."}
                final_response = await self._solve_internally(perception, metrics)
                yield {"event": "neural_synthesis", "data": {"token": final_response, "done": True}}
                asyncio.create_task(self._update_memory(user_input, final_response, perception, [], 1))
                
            elif decision == "ENGINE" and metrics["capable_engine"]:
                # LEVEL 2: ENGINE EXECUTION
                engine_name = metrics["capable_engine"]
                yield {"event": "activity", "data": f"Executing via internal engine: {engine_name}..."}
                
                engine_res = await self.engine_registry.execute(engine_name, user_input)
                
                # Standardize
                tool_res = {
                    "success": engine_res.get("success", False),
                    "message": engine_res.get("message", str(engine_res.get("data", ""))),
                    "data": engine_res.get("data"),
                    "agent": engine_name,
                    "engine": engine_res.get("engine")
                }
                
                yield {"event": "results", "data": [tool_res]}
                yield {"event": "neural_synthesis", "data": {"token": tool_res["message"], "done": True}}
                
                # Metrics (Step 7)
                self.metrics_registry["tasks_solved_engine"] += 1
                asyncio.create_task(self._update_memory(user_input, tool_res["message"], perception, [tool_res], 2))
                
            elif decision == "MEMORY" and metrics["memory_match_score"] > 0.75:
                 # LEVEL 1: MEMORY Shortcut
                 yield {"event": "activity", "data": "Direct Memory Match Detected. skipping planner..."}
                 final_response = await self._solve_internally(perception, metrics)
                 yield {"event": "neural_synthesis", "data": {"token": final_response, "done": True}}
                 asyncio.create_task(self._update_memory(user_input, final_response, perception, [], 1))

            else:
                # 3. NEURAL FALLBACK (v9.5)
                # v9.5 Neural Handoff: Local vs Cloud
                handoff_request = await self.handoff.route_inference(user_input, perception["context"])
                if handoff_request.get("target") == "local":
                     yield {"event": "activity", "data": f"Neural Handoff: Active. Routing to LOCAL ({handoff_request['provider']})..."}
                     # We tag the context but keep the placeholder synthesis call
                     perception["context"]["local_handoff"] = True
                else:
                     yield {"event": "activity", "data": "Routing to CLOUD infrastructure..."}
                
                if not self.llm_guard.allow_llm(user_input, metrics):
                    yield {"event": "error", "data": "LLM access restricted by Brain Policy."}
                    return

                yield {"event": "activity", "data": "Planning DAG Mission..."}
                goal = await self.goal_engine.create_goal(perception)
                task_graph = await self.planner.build_task_graph(goal, perception)
                yield {"event": "graph", "data": task_graph.to_dict()}
                
                yield {"event": "activity", "data": "Executing Mission Tasks..."}
                
                # v9.8.1: Dynamic Concurrency
                concurrency = await self._get_concurrency_limit(user_id)
                results = await self.executor.run(task_graph, perception, concurrency_limit=concurrency)
                yield {"event": "results", "data": [r.dict() if hasattr(r, "dict") else r for r in results]}
                
                yield {"event": "activity", "data": "Synthesizing Final Response..."}
                from ..engine import synthesize_streaming_response
                full_parts = []
                async for chunk in synthesize_streaming_response(results, perception["context"]):
                    if "token" in chunk: full_parts.append(chunk["token"])
                    yield chunk

                asyncio.create_task(self._update_memory(user_input, "".join(full_parts), perception, results, 4))

        except Exception as e:
            logger.error("[V8 Brain] Stream anomaly: %s", e)
            yield {"event": "error", "data": f"The neural stream encountered a logic drift: {str(e)}"}

    async def _get_concurrency_limit(self, user_id: str) -> int:
        """
        Sovereign v9.8.1: Dynamic Concurrency Discovery.
        Maps subscription_tier to parallel task semaphore capacity.
        """
        from backend.db.postgres import PostgresDB
        from sqlalchemy import text
        
        # Default for guests/failures
        default_limit = 2
        if not user_id or user_id.startswith("guest"):
            return default_limit

        try:
            # We use the session context manager from PostgresDB
            async with await PostgresDB.get_session() as session:
                query = text("SELECT subscription_tier FROM user_profiles WHERE uid = :uid")
                res = await session.execute(query, {"uid": user_id})
                tier = res.scalar() or "free"
                
                mapping = {
                    "premium": 10,
                    "pro": 5,
                    "free": 2
                }
                return mapping.get(tier.lower(), default_limit)
        except Exception as e:
            logger.warning(f"[Brain] Failed to fetch concurrency tier for {user_id}: {e}")
            return default_limit

    async def _perceive(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """Extract intent and 4-tier context."""
        from ...planner import detect_intent
        intent = await detect_intent(user_input)
        context = await self.memory.get_combined_context(user_id, session_id, user_input)
        context.update(kwargs)
        return {
            "input": user_input,
            "intent": intent,
            "context": context,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _brain_synthesis(self, results: List[ToolResult], goal: Any, perception: Dict[str, Any]) -> str:
        """
        Brain-Level Final Synthesis (v8.12).
        Orchestrates final response using structured data from agents.
        """
        from ..engine import synthesize_response
        
        # Format structured data for LLM synthesis if needed
        # Agents now return Pydantic models in .data
        formatted_results = []
        for r in results:
            if hasattr(r, "data") and hasattr(r.data, "dict"):
                 formatted_results.append(f"Agent {r.agent} Results: {json.dumps(r.data.dict())}")
            else:
                 formatted_results.append(str(r))

        response = await synthesize_response(results, perception["context"])
        
        # Reflection pass
        evaluation = await self.reflection.evaluate(response, goal, perception)
        if not evaluation["is_satisfactory"]:
            broadcast_mission_event(perception["user_id"], "reflection_retry", {"score": evaluation["score"]})
            response = await self.reflection.self_correct(response, evaluation, goal, perception)
        
        return response

    async def _solve_internally(self, perception: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        """LEVEL 1: Deterministic solution via memory/graph/templates."""
        context = perception.get("context", {})
        query = perception.get("input", "").lower()
        
        # 1. Rule-based Template Matches
        intent_type = perception["intent"].intent_type
        if intent_type == "greeting":
            return "Greetings. I am LeviBrain Core, operating via internal logic. How can I assist you today?"

        # 2. Knowledge Graph Resonance (Neo4j)
        graph_resonance = context.get("graph_resonance", [])
        if graph_resonance:
            # Format: Alice -RELATED_TO-> Bob
            matches = [f"{r['subject']} {r['relation'].lower().replace('_', ' ')} {r['object']}" for r in graph_resonance if r.get("subject")]
            if matches:
                return f"Internal Knowledge Graph Match: {', '.join(matches[:3])}."

        # 3. Memory Match Synthesis (Vector / T4 Identity)
        long_term = context.get("long_term", {})
        facts = long_term.get("raw", [])
        if facts:
            # Select most relevant fact based on query
            best_fact = facts[0].get("fact", "")
            return f"Retrieved Fact: {best_fact}"
            
        tier4 = context.get("tier4_traits", {})
        if tier4 and "archetype" in tier4:
             return f"Identity Resonance Matched: {tier4['archetype']} archetype active. Processing via internal traits."

        return "Internal logic synthesis complete. No direct fact match found, but system state is aligned."

    async def _update_memory(self, user_input: str, response: str, perception: Dict[str, Any], results: List[ToolResult], level: int = 4):
        """Trigger asynchronous memory updates and self-improvement loop (v8.14)."""
        user_id, session_id = perception["user_id"], perception["session_id"]
        if user_id and not str(user_id).startswith("guest:"):
            # 1. Episodic Memory Storage
            asyncio.create_task(self.memory.store_memory(user_id, session_id, user_input, response))
            
            # 2. Self-Improvement Loop (v8.14)
            # This handles fragility, pattern promotion, and optimization
            outcome = {
                "user_id": user_id,
                "query": user_input,
                "response": response,
                "intent": perception["intent"].intent_type,
                "level": level,
                "success": len(response) > 0, # Basic success check
                "score": 1.0 if level < 4 else 0.8, # Heuristic score
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            asyncio.create_task(SelfImprovementLoop.process_mission(user_id, outcome))
            broadcast_mission_event(user_id, "learning_feedback", outcome)
            
            # 3. Evolution Learning Pass (v8.15)
            # System learns from successful outcomes to build deterministic rules
            if outcome["success"] and level < 4:
                self.evolution_engine.learn(user_input, response)
                
            # v9.5 Recursive Patching: Persistent Self-Healing Queue
            if not outcome["success"]:
                try:
                    from backend.db.redis import r as redis_client, HAS_REDIS
                    if HAS_REDIS:
                        logger.info("[Sovereign] Logic Failure detected. Pushing to healing queue.")
                        redis_client.lpush("sovereign:failure_queue", json.dumps(outcome))
                        # Trigger threshold check (v9.8)
                        queue_len = redis_client.llen("sovereign:failure_queue")
                        if queue_len >= 5:
                             logger.warning(f"[Sovereign] Failure threshold reached ({queue_len}). Alerting Critic...")
                             from backend.core.critic_tasks import process_failure_queue
                             process_failure_queue.delay()
                except Exception as e:
                    logger.error(f"[Sovereign] Failed to queue failure for healing: {e}")

# Alias for backward compatibility
LeviBrainV8 = LeviBrainCoreController
