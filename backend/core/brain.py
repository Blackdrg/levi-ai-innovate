"""
Sovereign Brain v8.
The cognitive heart of LEVI-AI.
Orchestrates Perception, Goal-Setting, Planning, Execution, and Reflection.
"""

import logging
import uuid
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Union

from .perception import PerceptionEngine
from .goal_engine import GoalEngine
from .planner import DAGPlanner
from .executor import GraphExecutor
from .reflection import ReflectionEngine
from .context_manager import ContextManager
from backend.memory.manager import MemoryManager
from .orchestrator_types import ToolResult, IntentResult
from ..utils.kafka import SovereignKafka

logger = logging.getLogger(__name__)

class LeviBrainV8:
    """
    LeviBrain v8: High-Fidelity Cognitive Pipeline.
    Architecture: Perception -> Goal -> Planning -> Execution -> Reflection -> Memory.
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.perception = PerceptionEngine(self.memory)
        self.goal_engine = GoalEngine()
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reflection = ReflectionEngine()
        self.context = ContextManager()

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

    async def run(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        request_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LeviBrain v8: The main cognitive execution pass.
        7-Step Pipeline: Perception -> Goal -> Planning -> Execution -> Reflection -> Memory -> Response.
        """
        request_id = request_id or f"v8_{uuid.uuid4().hex[:8]}"
        mission_start = datetime.now(timezone.utc)
        logger.info("[V8 Brain] Starting Cognitive Mission: %s", request_id)
        
        # 1. PERCEPTION: Extract intent and context
        asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_STARTED", "request_id": request_id}))
        perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)
        
        # 2. GOAL CREATION: Formulate cognitive mission
        goal = await self.goal_engine.create_goal(perception)

        # 3. PLANNING (DAG): Decompose goal into task graph
        task_graph = await self.planner.build_task_graph(goal, perception)
        asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_PLANNED", "request_id": request_id, "graph": task_graph.dict()}))
        
        # 4. EXECUTION: Run the task graph in parallel
        results = await self.executor.execute(task_graph, perception)
        asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_EXECUTED", "request_id": request_id, "results": [r.dict() for r in results]}))

        # 5. REFLECTION LOOP: Evaluate and refine if necessary
        from .engine import synthesize_response
        draft_response = await synthesize_response(results, perception["context"])
        
        reflection = await self.reflection.evaluate(draft_response, goal, perception, results)
        
        if not reflection["is_satisfactory"]:
            logger.warning("[V8 Brain] Low fidelity mission (%.2f). Refining plan...", reflection["score"])
            task_graph = await self.planner.refine_plan(task_graph, reflection, goal, perception)
            results = await self.executor.execute(task_graph, perception)
            final_response = await synthesize_response(results, perception["context"])
        else:
            final_response = draft_response

        # 6. MEMORY UPDATE: Store results and context
        await self.memory.store(user_id, session_id, user_input, final_response, perception, results)

        # 7. MISSION AUDITING: Self-Evolution Loop
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
        asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_AUDITED", "request_id": request_id, "score": audit["total_score"]}))

        # 8. FINAL RESPONSE
        return {
            "response": final_response,
            "request_id": request_id,
            "intent": perception["intent"].intent_type,
            "goal": goal.dict(),
            "graph": task_graph.dict(),
            "results": [r.dict() for r in results],
            "audit": audit
        }

    async def _update_memory(self, user_id: str, session_id: str, user_input: str, response: str, perception: Dict[str, Any], results: List[ToolResult]):
        """Bridges results to the 4-tier memory ecosystem."""
        await self.memory.store(user_id, session_id, user_input, response, perception, results)

    async def stream(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        request_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Token-by-token cognitive streaming.
        Architecture: Metadata -> Perception -> Activity -> Execution -> Token Stream.
        """
        request_id = request_id or f"v8_stream_{uuid.uuid4().hex[:8]}"
        logger.info("[V8 Brain] Starting Streaming Mission: %s", request_id)

        # 1. Initial Metadata Pulse
        yield {"event": "metadata", "data": {"request_id": request_id, "status": "pulsing"}}

        try:
            # 2. Perception Pass
            perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)
            yield {"event": "activity", "data": f"Intent: {perception['intent'].intent_type.upper()}"}
            
            # 3. Goal & Planning
            goal = await self.goal_engine.create_goal(perception)
            task_graph = await self.planner.build_task_graph(goal, perception)
            yield {"event": "graph", "data": task_graph.dict()}
            yield {"event": "activity", "data": "Mission Graph constructed."}
            
            # 4. Execution Pass
            results = await self.executor.execute(task_graph, perception)
            yield {"event": "results", "data": [r.dict() for r in results]}
            yield {"event": "activity", "data": f"Mission execution complete ({len(results)} nodes processed)."}
            
            # 5. Streaming Synthesis
            from .engine import synthesize_streaming_response
            
            full_response_parts = []
            async for chunk in synthesize_streaming_response(results, perception["context"]):
                if "token" in chunk:
                    full_response_parts.append(chunk["token"])
                yield chunk

            # 6. Memory Update (Background)
            full_response = "".join(full_response_parts)
            asyncio.create_task(self._update_memory(user_id, session_id, user_input, full_response, perception, results))

        except Exception as e:
            logger.error("[V8 Brain] Streaming anomaly: %s", e)
            yield {"event": "error", "data": "The cognitive stream encountered a quantum misalignment."}
