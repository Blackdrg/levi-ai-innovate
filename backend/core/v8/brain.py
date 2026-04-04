import logging
import uuid
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Union

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
from .handoff import NeuralHandoffManager
from .sync_engine import SovereignSync
from .engine_registry import EngineRegistry
from .evolution_engine import EvolutionEngine
from .self_improvement import SelfImprovementLoop
from backend.agents.consensus_agent import ConsensusAgentV11
from backend.memory.manager import MemoryManager
from ..orchestrator_types import ToolResult, IntentResult
from backend.api.v8.telemetry import broadcast_mission_event
from backend.utils.usage import count_tokens, estimate_cost

logger = logging.getLogger(__name__)

class LeviBrainCoreController:
    """
    LeviBrain Core Controller (v13.0.0 "Absolute Monolith")
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
        self.learning = LearningLoopV13() # Graduated
        self.decision_engine = DecisionEngine()
        self.llm_guard = LLMGuard()
        self.handoff = NeuralHandoffManager()
        
        # Self-Correction State (v13.0)
        self.failure_buffer: List[Dict[str, Any]] = []
        
        # Engine Registry Initialization (v13.0 Monolith)
        self.engine_registry = EngineRegistry()
        self.engine_registry.register("deterministic", DeterministicEngine())
        self.engine_registry.register("code", CodeEngine())
        self.engine_registry.register("data", DataEngine())
        self.engine_registry.register("knowledge", KnowledgeEngine())
        
        self.evolution_engine = EvolutionEngine()
        
        # Execution Metrics (v13.0)
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
        Unified Cognitive Entry Point v13.0.0.
        Routes the mission to either the Batch or Streaming pipeline.
        """
        if streaming:
            return self.run_mission_stream(user_input, user_id, session_id, **kwargs)
        else:
            return await self.run_mission_sync(user_input, user_id, session_id, **kwargs)

    async def run_mission_sync(self, input_text: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """High-fidelity synchronous mission execution (v13.0.0)."""
        user_input = input_text
        request_id = f"v13_{uuid.uuid4().hex[:8]}"
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
        # Graduation v13.0: Checks both local and foreign collective rules
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
            
        elif decision == "EXPERT_REVIEW":
            # Phase 8: Swarm Consensus Adjudication (Expert Review v11.0)
            logger.info("[LeviBrain] Decision: EXPERT_REVIEW (Triggering Swarm Consensus)...")
            
            # Goal and Planning required for agent tasks
            goal = await self.goal_engine.create_goal(perception)
            task_graph = await self.planner.build_task_graph(goal, perception)
            
            # Execute Mission (Parallel Agents)
            results = await self.executor.run(task_graph, perception, concurrency_limit=5)
            
            # Consensus Adjudication
            from backend.agents.consensus_agent import ConsensusInput
            consensus_agent = ConsensusAgentV11()
            consensus_input = ConsensusInput(
                goal=goal.objective,
                candidates=results,
                context=perception["context"]
            )
            consensus_res = await consensus_agent.run(consensus_input)
            
            if consensus_res.get("success"):
                winner_result = consensus_res.get("data", {}).get("winner")
                # Normalize result shape
                if isinstance(winner_result, dict):
                    final_response = winner_result.get("message", winner_result.get("data", ""))
                else:
                    final_response = str(winner_result)
            else:
                final_response = "Swarm consensus failed to reach high-fidelity agreement. Falling back to local intelligence."
            
            self.metrics_registry["tasks_solved_engine"] += 1
            execution_level = 3
            
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

        # 6. MEMORY UPDATE, LEARNING & SYNC (v12.0)
        latency = (datetime.now(timezone.utc) - mission_start).total_seconds() * 1000
        await self._update_memory(user_input, final_response, perception, results, execution_level, latency=latency)
        
        # 6.5 DCN Global Resonance Sync
        if execution_level < 4: # Only sync successful deterministic/engine outcomes
             asyncio.create_task(SovereignSync.sync_with_collective_hub())

        # 7. RESPONSE SYNCHRONIZATION
        return {
            "response": final_response,
            "request_id": request_id,
            "decision": decision,
            "latency_ms": latency,
            "results": [r.dict() if hasattr(r, "dict") else r for r in results],
            "metrics": self.metrics_registry
        }

    async def run_mission_stream(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        High-Fidelity SSE Streaming Pass (v13.0.0).
        Architecture: Metadata -> Perception -> Activity -> Execution -> Token Stream.
        """
        request_id = f"v13_stream_{uuid.uuid4().hex[:8]}"
        logger.info("[V13 Brain] Starting Streaming Mission: %s", request_id)

        yield {"event": "metadata", "data": {"request_id": request_id, "status": "pulsing", "version": "v13.0.0"}}
        yield {"event": "mission_start", "data": {"request_id": request_id, "input": user_input}}

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

        # Evolution Shortcut (v13.0)
        evo_match = self.evolution_engine.apply(user_input)
        if evo_match:
            yield {"event": "activity", "data": "Evolution Pattern Match Detected. Synthesizing solution..."}
            yield {"event": "neural_synthesis", "data": {"token": evo_match, "done": True}}
            return

        try:
            if decision == "RULE" and metrics["has_rule"]:
                # v13.0: Deterministic Rule Finality
                yield {"event": "activity", "data": "Deterministic Rule Hit (v13). Returning solution..."}
                final_response = metrics["rule_data"]
                yield {"event": "neural_synthesis", "data": {"token": final_response, "done": True}}
                asyncio.create_task(self._update_memory(user_input, final_response, perception, [], 1))
                
            elif decision == "INTERNAL":
                # LEVEL 1: INTERNAL BRAIN LOGIC
                yield {"event": "activity", "data": "Processing via Internal Monolith Logic..."}
                final_response = await self._solve_internally(perception, metrics)
                yield {"event": "neural_synthesis", "data": {"token": final_response, "done": True}}
                asyncio.create_task(self._update_memory(user_input, final_response, perception, [], 1))
                
            elif decision == "ENGINE" and metrics["capable_engine"]:
                # LEVEL 2: ENGINE EXECUTION (v13.0)
                engine_name = metrics["capable_engine"]
                yield {"event": "activity", "data": f"Executing via engine registry: {engine_name}..."}
                
                engine_res = await self.engine_registry.execute(engine_name, user_input)
                
                tool_res = {
                    "success": engine_res.get("success", False),
                    "message": engine_res.get("message", str(engine_res.get("data", ""))),
                    "data": engine_res.get("data"),
                    "agent": engine_name,
                    "engine": engine_res.get("engine")
                }
                
                yield {"event": "results", "data": [tool_res]}
                yield {"event": "neural_synthesis", "data": {"token": tool_res["message"], "done": True}}
                
                self.metrics_registry["tasks_solved_engine"] += 1
                asyncio.create_task(self._update_memory(user_input, tool_res["message"], perception, [tool_res], 2))
                
            elif decision == "MEMORY" and metrics["memory_match_score"] > 0.75:
                 # LEVEL 1: MEMORY Shortcut (HNSW)
                 yield {"event": "activity", "data": "HNSW Vector Vault Match Detected. Skipping planner..."}
                 final_response = await self._solve_internally(perception, metrics)
                 yield {"event": "neural_synthesis", "data": {"token": final_response, "done": True}}
                 asyncio.create_task(self._update_memory(user_input, final_response, perception, [], 1))

            else:
                # 3. NEURAL FALLBACK (v13.0 "Council of Models")
                handoff_request = await self.handoff.route_inference(user_input, perception["context"])
                if handoff_request.get("target") == "local":
                     yield {"event": "activity", "data": f"Neural Handoff: Active. Routing to LOCAL ({handoff_request['provider']})..."}
                     perception["context"]["local_handoff"] = True
                else:
                     yield {"event": "activity", "data": "Routing mission to SOVEREIGN CLOUD swarm..."}
                
                if not self.llm_guard.allow_llm(user_input, metrics):
                    yield {"event": "error", "data": "LLM access restricted by Brain Policy."}
                    return

                yield {"event": "activity", "data": "Building mission task graph (v13.0)..."}
                goal = await self.goal_engine.create_goal(perception)
                task_graph = await self.planner.build_task_graph(goal, perception)
                yield {"event": "graph", "data": task_graph.to_dict()}
                
                yield {"event": "activity", "data": "Executing mission swarm..."}
                concurrency = await self._get_concurrency_limit(user_id)
                results = await self.executor.run(task_graph, perception, concurrency_limit=concurrency)
                yield {"event": "results", "data": [r.dict() if hasattr(r, "dict") else r for r in results]}
                
                yield {"event": "activity", "data": "Synthesizing Absolute Monolith Response..."}
                from ..engine import synthesize_streaming_response
                full_parts = []
                async for chunk in synthesize_streaming_response(results, perception["context"]):
                    if "token" in chunk: full_parts.append(chunk["token"])
                    yield chunk

                asyncio.create_task(self._update_memory(user_input, "".join(full_parts), perception, results, 4))

        except Exception as e:
            logger.error("[V13 Brain] Stream anomaly: %s", e)
            yield {"event": "error", "data": f"The Absolute Monolith encountered a logic flux: {str(e)}"}

    async def _get_concurrency_limit(self, user_id: str) -> int:
        """
        Sovereign v13.0.0: Dynamic Concurrency Discovery (SQL Sync).
        Maps subscription_tier to parallel task semaphore capacity via Postgres.
        """
        from backend.db.postgres_db import get_read_session
        from sqlalchemy import text
        
        default_limit = 2
        if not user_id or user_id.startswith("guest"):
            return default_limit

        try:
            async with get_read_session() as session:
                query = text("SELECT subscription_tier FROM user_profiles WHERE uid = :uid")
                res = await session.execute(query, {"uid": user_id})
                tier = res.scalar() or "free"
                
                mapping = {
                    "premium": 20, # Higher concurrency for v13 graduation
                    "pro": 10,
                    "free": 4
                }
                return mapping.get(tier.lower(), default_limit)
        except Exception as e:
            logger.warning(f"[Brain-v13] Failed to fetch concurrency tier for {user_id}: {e}")
            return default_limit

    async def _perceive(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """Extract intent and 4-tier context."""
        from ..planner import detect_intent
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

    async def _update_memory(self, user_input: str, response: str, perception: Dict[str, Any], results: List[ToolResult], level: int = 4, latency: float = 0.0):
        """Trigger asynchronous memory updates and self-improvement loop (v11.0)."""
        user_id, session_id = perception["user_id"], perception["session_id"]
        if user_id and not str(user_id).startswith("guest:"):
            # 1. Episodic Memory Storage
            asyncio.create_task(self.memory.store_memory(user_id, session_id, user_input, response))
            
            # 2. Self-Improvement Loop (v8.14)
            # This handles fragility, pattern promotion, and optimization
            agent_tokens = sum(getattr(r, 'total_tokens', 0) for r in results)
            # If agents didn't provide tokens (e.g. local models), estimate locally
            if agent_tokens == 0:
                agent_tokens = count_tokens(response)
            
            total_mission_tokens = count_tokens(user_input) + agent_tokens
            
            outcome = {
                "user_id": user_id,
                "query": user_input,
                "response": response,
                "intent": perception["intent"].intent_type,
                "level": level,
                "success": len(response) > 0, # Basic success check
                "score": 1.0 if level < 4 else 0.8, # Heuristic score
                "latency_ms": latency,
                "results": [r.dict() if hasattr(r, "dict") else r for r in results],
                "token_count": total_mission_tokens, 
                "cost_usd": estimate_cost(total_mission_tokens),
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

    async def run_autonomous_loop(self, user_id: str):
        """
        Phase 7: True Autonomy Loop.
        Implements: detect_goal() -> plan() -> execute() -> evaluate() -> learn().
        """
        logger.info(f"[Autonomy] Starting autonomous cycle for {user_id}")
        while True:
            try:
                # 1. Long-Horizon Resumption (Phase 7)
                pending_goals = await self.goal_engine.get_pending_goals(user_id)
                goal = None
                if pending_goals:
                    goal = pending_goals[0]
                    logger.info(f"[Autonomy] Pursuing persistent goal: {goal.objective}")
                else:
                    # 2. Detect Goal (Self-Initiated Curiosity)
                    if await self._is_idle(user_id):
                        goal = await self.goal_engine.create_goal({
                            "input": "Discover new technological advancements relevant to user interests",
                            "intent": "search",
                            "user_id": user_id,
                            "context": await self.memory.get_combined_context(user_id, "curiosity_session")
                        })
                
                if goal:
                    # 3. Plan & Execute
                    task_graph = await self.planner.build_task_graph(goal, {"user_id": user_id})
                    results = await self.executor.run(task_graph, {"user_id": user_id})
                    # Update mission timestamp
                    if HAS_REDIS:
                        redis_client.set(f"user:{user_id}:last_mission", datetime.now(timezone.utc).isoformat())
                    
                    # 4. Evaluate & Learn
                    await self._update_memory("Autonomous Mission", "Complete", {"user_id": user_id, "session_id": "autonomy"}, results, level=1)
                
                # 5. Housekeeping
                await self.perform_housekeeping(user_id)
                
            except Exception as e:
                logger.error(f"[Autonomy] Cycle anomaly: {e}")
            
            await asyncio.sleep(3600) # Pulse every hour

    async def _is_idle(self, user_id: str) -> bool:
        """Determines if the user has been inactive long enough to trigger curiosity missions."""
        if not HAS_REDIS: return True
        last_mission = redis_client.get(f"user:{user_id}:last_mission")
        if not last_mission: return True
        try:
            last_dt = datetime.fromisoformat(last_mission.decode() if isinstance(last_mission, bytes) else last_mission)
            if last_dt.tzinfo is None: last_dt = last_dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - last_dt).total_seconds() > 14400 # 4 hours
        except: return True

    async def perform_housekeeping(self, user_id: str):
        """Autonomous system maintenance: memory optimization and workflow cleaning."""
        logger.info(f"[Housekeeping] Running maintenance for {user_id}...")
        
        # 1. Memory Cleaning (Dreaming)
        from .dreaming_task import DreamingTask
        await DreamingTask.trigger_force(user_id)
        
        # 2. Workflow Optimization
        from .self_improvement import SelfImprovementLoop
        await SelfImprovementLoop.run_optimization_cycle()
        
        broadcast_mission_event(user_id, "housekeeping_complete", {"status": "optimized"})

# Alias for backward compatibility
LeviBrainV8 = LeviBrainCoreController
