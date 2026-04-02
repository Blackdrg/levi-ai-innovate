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

    async def run(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Any:
        request_id = f"v8_{uuid.uuid4().hex[:8]}"
        logger.info("[V8 Brain] Starting Cognitive Mission: %s", request_id)

        # 1. Perception Layer
        perception = await self._perceive(user_input, user_id, session_id, **kwargs)
        await emit_brain_event("perception", {"request_id": request_id, "intent": str(perception["intent"])})
        
        # 2. Goal Engine
        goal = await self.goal_engine.create_goal(perception)
        await emit_brain_event("goal", {"request_id": request_id, "objective": goal.objective})

        # 3. Planning Engine (DAG)
        task_graph = await self.planner.build_task_graph(goal, perception)
        await emit_brain_event("planning", {"request_id": request_id, "graph": task_graph.to_dict()})
        
        # 4. Execution Engine (Parallel)
        results = await self.executor.run(task_graph, perception)
        await emit_brain_event("execution", {"request_id": request_id, "results_count": len(results)})

        # 5. Reflection Engine (Critic v2)
        final_response = await self._reflect_and_synthesize(results, goal, perception)

        # 6. Memory Update & Learning
        await self._update_memory(user_input, final_response, perception, results)
        await emit_brain_event("response", {"request_id": request_id, "response": final_response[:100]})

        return {
            "response": final_response,
            "request_id": request_id,
            "goal": goal.dict(),
            "graph": task_graph.to_dict(),
            "results": [r.dict() for r in results]
        }

    async def _perceive(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """Extract intent, entities, emotion, and context (Hybrid)."""
        from ..planner import detect_intent
        intent = await detect_intent(user_input)
        
        # Combine 4-tier context
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
        # Initial synthesis pass
        from ..engine import synthesize_response
        response = await synthesize_response(results, perception["context"])
        
        # Reflection V8 Loop
        evaluation = await self.reflection.evaluate(response, goal, perception)
        
        if not evaluation["is_satisfactory"]:
            await emit_brain_event("reflection.retry", {"score": evaluation["score"], "issues": evaluation["issues"]})
            response = await self.reflection.self_correct(response, evaluation, goal, perception)
        else:
            await emit_brain_event("reflection.success", {"score": evaluation["score"]})
            
        return response

    async def _update_memory(self, user_input: str, response: str, perception: Dict[str, Any], results: List[ToolResult]):
        """Trigger asynchronous memory and learning updates."""
        user_id = perception["user_id"]
        session_id = perception["session_id"]
        
        if user_id and not str(user_id).startswith("guest:"):
            # V8 Tiered update
            asyncio.create_task(self.memory.store_memory(user_id, session_id, user_input, response))
            
            # Learning emission
            event = {
                "user_id": user_id,
                "query": user_input,
                "response": response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            asyncio.create_task(LeviKafkaClient.send_event("learning.feedback", event))
