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
from backend.memory.manager import MemoryManager
from ..orchestrator_types import ToolResult, IntentResult
from ...kafka_client import emit_brain_event

logger = logging.getLogger(__name__)

class LeviBrainV8:
    """
    LeviBrain v8: Real Intelligence Architecture
    Cognitive Pipeline: Perception -> Goal -> Planning -> Execution -> Reflection -> Memory
    
    Integrated with Kafka for asynchronous service orchestration and learning.
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.goal_engine = GoalEngine()
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reflection = ReflectionEngine()
        self.learning = LearningLoopV8()

    async def route(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Unified Cognitive Entry Point v8.
        Routes the mission to either the Batch or Streaming pipeline.
        """
        if streaming:
            return self.stream(user_input, user_id, session_id, **kwargs)
        else:
            return await self.run(user_input, user_id, session_id, **kwargs)

    async def run(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        request_id = f"v8_{uuid.uuid4().hex[:8]}"
        mission_start = datetime.now(timezone.utc)
        logger.info("[V8 Brain] Starting Cognitive Mission: %s", request_id)

        # 1. PERCEPTION
        perception = await self._perceive(user_input, user_id, session_id, **kwargs)
        await emit_brain_event("perception", {"request_id": request_id, "intent": str(perception["intent"])})
        
        # 2. GOAL CREATION
        goal = await self.goal_engine.create_goal(perception)
        await emit_brain_event("goal", {"request_id": request_id, "objective": goal.objective})

        # 3. PLANNING (DAG)
        task_graph = await self.planner.build_task_graph(goal, perception)
        await emit_brain_event("planning", {"request_id": request_id, "graph": task_graph.to_dict()})
        
        # 4. EXECUTION
        results = await self.executor.run(task_graph, perception)
        await emit_brain_event("execution", {"request_id": request_id, "results_count": len(results)})

        # 5. REFLECTION & SYNTHESIS
        final_response = await self._reflect_and_synthesize(results, goal, perception)

        # 6. MEMORY UPDATE
        await self._update_memory(user_input, final_response, perception, results)

        # 7. MISSION AUDITING (8th Step)
        from backend.evaluation.evaluator import AutomatedEvaluator
        latency = (datetime.now(timezone.utc) - mission_start).total_seconds() * 1000
        audit = await AutomatedEvaluator.evaluate_transaction(
            user_id=user_id,
            session_id=session_id,
            user_input=user_input,
            response=final_response,
            goals=[goal.objective] + goal.success_criteria,
            tool_results=[r.dict() for r in results],
            latency_ms=latency
        )
        await emit_brain_event("audit", {"request_id": request_id, "score": audit["total_score"]})

        # 8. RESPONSE SYNCHRONIZATION
        return {
            "response": final_response,
            "request_id": request_id,
            "goal": goal.dict(),
            "graph": task_graph.to_dict(),
            "results": [r.dict() for r in results],
            "audit": audit
        }

    async def stream(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        High-Fidelity SSE Streaming Pass.
        Architecture: Metadata -> Perception -> Activity -> Execution -> Token Stream.
        """
        request_id = f"v8_stream_{uuid.uuid4().hex[:8]}"
        logger.info("[V8 Brain] Starting Streaming Mission: %s", request_id)

        yield {"event": "metadata", "data": {"request_id": request_id, "status": "pulsing"}}

        try:
            # 1. Perception
            perception = await self._perceive(user_input, user_id, session_id, **kwargs)
            yield {"event": "activity", "data": f"Intent: {perception['intent'].intent_type.upper()}"}
            
            # 2. Planning
            goal = await self.goal_engine.create_goal(perception)
            task_graph = await self.planner.build_task_graph(goal, perception)
            yield {"event": "graph", "data": task_graph.to_dict()}
            
            # 3. Execution
            yield {"event": "activity", "data": "Executing Mission Tasks..."}
            results = await self.executor.run(task_graph, perception)
            yield {"event": "results", "data": [r.dict() for r in results]}
            
            # 4. Neural Synthesis Stream
            from ..engine import synthesize_streaming_response
            full_parts = []
            async for chunk in synthesize_streaming_response(results, perception["context"]):
                if "token" in chunk: full_parts.append(chunk["token"])
                yield chunk

            # 5. Background Crystallization
            asyncio.create_task(self._update_memory(user_input, "".join(full_parts), perception, results))

        except Exception as e:
            logger.error("[V8 Brain] Stream anomaly: %s", e)
            yield {"event": "error", "data": "The neural stream encountered a quantum misalignment."}

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

    async def _reflect_and_synthesize(self, results: List[ToolResult], goal: Any, perception: Dict[str, Any]) -> str:
        """Synthesize final response with reflection pass."""
        from ..engine import synthesize_response
        response = await synthesize_response(results, perception["context"])
        
        evaluation = await self.reflection.evaluate(response, goal, perception)
        if not evaluation["is_satisfactory"]:
            await emit_brain_event("reflection.retry", {"score": evaluation["score"]})
            response = await self.reflection.self_correct(response, evaluation, goal, perception)
        
        return response

    async def _update_memory(self, user_input: str, response: str, perception: Dict[str, Any], results: List[ToolResult]):
        """Trigger asynchronous memory updates."""
        user_id, session_id = perception["user_id"], perception["session_id"]
        if user_id and not str(user_id).startswith("guest:"):
            asyncio.create_task(self.memory.store_memory(user_id, session_id, user_input, response))
            
            # Mission audit for evolutionary learning
            audit_event = {
                "user_id": user_id,
                "query": user_input,
                "response": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            asyncio.create_task(emit_brain_event("learning.feedback", audit_event))
