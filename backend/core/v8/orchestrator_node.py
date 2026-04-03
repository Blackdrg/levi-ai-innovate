"""
Sovereign V8 Orchestrator Node.
The unified cognitive heart of the LEVI-AI Absolute Monolith.
Consolidates Perception, Planning, execution, and Reflection into a single, Kafka-free process.
"""

import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator

from .goal_engine import GoalEngine
from .planner import DAGPlanner
from .executor import GraphExecutor
from .critic import ReflectionEngine
from backend.memory.manager import MemoryManager
from backend.api.v8.telemetry import broadcast_mission_event

logger = logging.getLogger(__name__)

class SovereignOrchestrator:
    """
    Unified Orchestrator for the Sovereign V8 Monolith.
    Eliminates the distributive overhead of Kafka/Zookeeper.
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.goal_engine = GoalEngine()
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reflection = ReflectionEngine()

    async def execute_mission(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a complete cognitive mission end-to-end.
        """
        request_id = f"v8_{uuid.uuid4().hex[:8]}"
        mission_start = datetime.now(timezone.utc)
        logger.info(f"[Orchestrator-Node] Mission Started: {request_id}")

        # 1. PERCEPTION (Intent + Context)
        from backend.core.perception import detect_intent
        intent = await detect_intent(user_input)
        
        # Hydrate context from 4-tier memory
        merged_context = await self.memory.get_combined_context(user_id, session_id, user_input)
        if context:
            merged_context.update(context)
            
        perception = {
            "input": user_input,
            "intent": intent,
            "context": merged_context,
            "user_id": user_id,
            "session_id": session_id,
            "request_id": request_id
        }
        
        # Telemetry Pulse
        broadcast_mission_event(user_id, "perception", {"request_id": request_id, "intent": str(intent)})

        # 2. GOAL FORMATION
        goal = await self.goal_engine.create_goal(perception)
        broadcast_mission_event(user_id, "goal", {"request_id": request_id, "objective": goal.objective})

        # 3. DAG PLANNING
        task_graph = await self.planner.build_task_graph(goal, perception)
        broadcast_mission_event(user_id, "planning", {"request_id": request_id, "graph": task_graph.to_dict()})

        # 4. PARALLEL WAVE EXECUTION
        results = await self.executor.run(task_graph, perception)
        broadcast_mission_event(user_id, "execution", {"request_id": request_id, "results_count": len(results)})

        # 5. REFLECTION & SYNTHESIS
        from backend.services.orchestrator.engine import synthesize_response
        response = await synthesize_response(results, merged_context)
        
        evaluation = await self.reflection.evaluate(response, goal, perception)
        if not evaluation["is_satisfactory"]:
            broadcast_mission_event(user_id, "reflection_retry", {"score": evaluation["score"]})
            response = await self.reflection.self_correct(response, evaluation, goal, perception)
            
        # 6. MEMORY CRYSTALLIZATION
        asyncio.create_task(self.memory.store_memory(user_id, session_id, user_input, response))
        
        # 7. FINAL AUDIT
        from backend.evaluation.evaluator import AutomatedEvaluator
        latency = (datetime.now(timezone.utc) - mission_start).total_seconds() * 1000
        audit = await AutomatedEvaluator.evaluate_transaction(
            user_id=user_id,
            session_id=session_id,
            user_input=user_input,
            response=response,
            goals=[goal.objective] + goal.success_criteria,
            tool_results=[r.dict() for r in results],
            latency_ms=latency
        )
        broadcast_mission_event(user_id, "mission_final", {"request_id": request_id, "fidelity": audit["total_score"]})

        return {
            "response": response,
            "request_id": request_id,
            "goal": goal.dict(),
            "results": [r.dict() for r in results],
            "audit": audit,
            "status": "accomplished"
        }

    async def execute_mission_streaming(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        High-Fidelity SSE Streaming Mission.
        Yields: Metadata -> Perception -> Activity -> Execution Results -> Token Stream.
        """
        request_id = f"v8_stream_{uuid.uuid4().hex[:8]}"
        mission_start = asyncio.get_event_loop().time()
        logger.info(f"[Orchestrator-Node] Streaming Mission Started: {request_id}")

        yield {"event": "metadata", "data": {"request_id": request_id, "status": "pulsing"}}

        try:
            # 1. PERCEPTION
            from backend.core.perception import detect_intent
            intent = await detect_intent(user_input)
            
            merged_context = await self.memory.get_combined_context(user_id, session_id, user_input)
            if context:
                merged_context.update(context)
                
            perception = {
                "input": user_input,
                "intent": intent,
                "context": merged_context,
                "user_id": user_id,
                "session_id": session_id,
                "request_id": request_id
            }
            
            broadcast_mission_event(user_id, "perception", {"request_id": request_id, "intent": str(intent)})
            yield {"event": "activity", "data": f"Intent Decrypted: {intent.intent_type.upper()}"}

            # 2. GOAL FORMATION
            goal = await self.goal_engine.create_goal(perception)
            broadcast_mission_event(user_id, "goal", {"request_id": request_id, "objective": goal.objective})
            yield {"event": "goal", "data": goal.dict()}

            # 3. DAG PLANNING
            task_graph = await self.planner.build_task_graph(goal, perception)
            broadcast_mission_event(user_id, "planning", {"request_id": request_id, "graph": task_graph.to_dict()})
            yield {"event": "graph", "data": task_graph.to_dict()}

            # 4. PARALLEL WAVE EXECUTION
            yield {"event": "activity", "data": "Executing Autonomous Task Waves..."}
            results = await self.executor.run(task_graph, perception)
            broadcast_mission_event(user_id, "execution", {"request_id": request_id, "results_count": len(results)})
            yield {"event": "results", "data": [r.dict() for r in results]}

            # 5. NEURAL SYNTHESIS STREAM
            from backend.services.orchestrator.engine import synthesize_streaming_response
            full_response_parts = []
            async for chunk in synthesize_streaming_response(results, merged_context):
                if "token" in chunk:
                    full_response_parts.append(chunk["token"])
                yield chunk
            
            final_response = "".join(full_response_parts)

            # 6. REFLECTION & MEMORY (Background)
            asyncio.create_task(self._finalize_mission_background(
                final_response, goal, perception, results, mission_start
            ))

        except Exception as e:
            logger.error(f"[Orchestrator-Node] Streaming failure: {e}")
            yield {"event": "error", "data": f"Neural stream misalignment: {str(e)}"}

    async def _finalize_mission_background(self, response, goal, perception, results, start_time):
        """Asynchronous mission finalization for streaming missions."""
        user_id = perception["user_id"]
        session_id = perception["session_id"]
        request_id = perception["request_id"]

        # 1. Reflection Audit
        evaluation = await self.reflection.evaluate(response, goal, perception)
        if not evaluation["is_satisfactory"]:
             broadcast_mission_event(user_id, "reflection_retry", {"score": evaluation["score"]})
             # Note: For streaming, we can't 're-stream' easily here, but we record the need for evolution
        
        # 2. Memory Crystallization
        await self.memory.store_memory(user_id, session_id, perception["input"], response)
        
        # 3. Final Evolutionary Audit
        from backend.evaluation.evaluator import AutomatedEvaluator
        latency = (asyncio.get_event_loop().time() - start_time) * 1000
        audit = await AutomatedEvaluator.evaluate_transaction(
            user_id=user_id,
            session_id=session_id,
            user_input=perception["input"],
            response=response,
            goals=[goal.objective] + goal.success_criteria,
            tool_results=[r.dict() for r in results],
            latency_ms=latency
        )
        broadcast_mission_event(user_id, "mission_final", {"request_id": request_id, "fidelity": audit["total_score"]})
