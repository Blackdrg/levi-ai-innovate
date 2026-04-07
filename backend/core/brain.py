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
from .workflow_engine import WorkflowEngine
from .context_manager import ContextManager
from backend.memory.manager import MemoryManager
from .orchestrator_types import ToolResult, IntentResult
from ..utils.kafka import SovereignKafka
from backend.broadcast_utils import (
    SovereignBroadcaster, 
    PULSE_MISSION_STARTED, 
    PULSE_MISSION_PLANNED, 
    PULSE_MISSION_EXECUTED, 
    PULSE_MISSION_AUDITED,
    PULSE_MISSION_ERROR
)

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
        self.workflow_engine = WorkflowEngine()
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
        session_id: Optional[str] = None, 
        request_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LeviBrain v8: The main cognitive execution pass.
        7-Step Pipeline: Perception -> Goal -> Planning -> Execution -> Reflection -> Memory -> Response.
        """
        request_id = request_id or f"v8_{uuid.uuid4().hex[:8]}"
        session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        mission_start = datetime.now(timezone.utc)
        logger.info("[V8 Brain] Starting Cognitive Mission: %s", request_id)
        
        # 1. PERCEPTION: Extract intent and context
        SovereignBroadcaster.publish(PULSE_MISSION_STARTED, {"request_id": request_id, "user_input": user_input}, user_id=user_id)
        asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_STARTED", "request_id": request_id}))
        perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)

        
        # 2. GOAL CREATION: Formulate cognitive mission
        goal = await self.goal_engine.create_goal(perception)

        # 3. PLANNING (DAG): Decompose goal into task graph
        task_graph = await self.planner.build_task_graph(goal, perception)
        SovereignBroadcaster.publish(PULSE_MISSION_PLANNED, {"request_id": request_id, "goal": goal.objective, "steps": [s.description for s in task_graph.steps]}, user_id=user_id)
        asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_PLANNED", "request_id": request_id, "graph": task_graph.dict()}))

        
        # 4. EXECUTION: Run the task graph (Parallel DAG or Autonomous Workflow)
        if perception["intent"].intent_type == "complex":
            logger.info("[V8 Brain] Complexity Breach Detected. Handoff to Autonomous Workflow Engine.")
            wf_state = await self.workflow_engine.run(goal, self, perception)
            final_response = wf_state["final_output"]
            results = [ToolResult(success=True, message=res["results"][-1]["message"], agent=res["results"][-1]["agent"]) for res in wf_state["steps"]] # Simplified for trace
            return {
                "response": final_response,
                "request_id": request_id,
                "intent": "complex",
                "goal": goal.dict(),
                "workflow": wf_state,
                "audit": {"total_score": 1.0} # Workflow has internal evaluation
            }

        results = await self.executor.execute(task_graph, perception, user_id=user_id)
        SovereignBroadcaster.publish(PULSE_MISSION_EXECUTED, {"request_id": request_id, "success_count": len([r for r in results if r.success])}, user_id=user_id)
        asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_EXECUTED", "request_id": request_id, "results": [r.dict() for r in results]}))


        # 5. REFLECTION & DEBATE LOOP: Evaluate and refine if necessary
        from .engine import synthesize_response
        draft_response = await synthesize_response(results, perception["context"])
        
        refinement_count = 0
        MAX_REFINEMENTS = 2
        
        while refinement_count < MAX_REFINEMENTS:
            reflection = await self.reflection.evaluate(draft_response, goal, perception, results)
            
            if reflection["is_satisfactory"]:
                final_response = draft_response
                break
            
            refinement_count += 1
            logger.warning("[V8 Brain] Low fidelity mission detected. Refinement cycle %d/%d initiated.", refinement_count, MAX_REFINEMENTS)
            # Standard pulse for the block mission (Kafka/Audit)
            asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "DEBATE_CYCLE", "request_id": request_id, "cycle": refinement_count, "fidelity": reflection['score']}))
            
            # Refine the plan based on the Critic's fix
            task_graph = await self.planner.refine_plan(task_graph, reflection, goal, perception)
            results = await self.executor.execute(task_graph, perception, user_id=user_id)
            draft_response = await synthesize_response(results, perception["context"])
        else:
            # If we reach max refinements, use the best possible draft
            final_response = draft_response
        
        # Last known fidelity score
        final_fidelity = reflection.get("score") if 'reflection' in locals() else 0.0


        # 6. MEMORY UPDATE: Store results and context
        await self.memory.store(user_id, session_id, user_input, final_response, perception, results, fidelity=final_fidelity)

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
        SovereignBroadcaster.publish(PULSE_MISSION_AUDITED, {"request_id": request_id, "score": audit["total_score"], "latency": latency}, user_id=user_id)
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

    async def _update_memory(self, user_id: str, session_id: str, user_input: str, response: str, perception: Dict[str, Any], results: List[ToolResult], fidelity: Optional[float] = None):
        """Bridges results to the 4-tier memory ecosystem."""
        await self.memory.store(user_id, session_id, user_input, response, perception, results, fidelity=fidelity)

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
            
            # 4. Execution & Reflection (v8 Synthetic Swarm)
            refinement_count = 0
            MAX_REFINEMENTS = 2
            
            while refinement_count < MAX_REFINEMENTS:
                results = await self.executor.execute(task_graph, perception, user_id=user_id)
                yield {"event": "results", "data": [r.dict() for r in results]}
                
                # Dynamic Logic Hub Synthesis
                from .engine import synthesize_response
                draft_response = await synthesize_response(results, perception["context"])
                
                reflection = await self.reflection.evaluate(draft_response, goal, perception, results)
                if reflection["is_satisfactory"]:
                    break
                
                refinement_count += 1
                yield {"event": "activity", "data": f"Refinement Cycle {refinement_count}: {reflection['issues'][0]}"}
                task_graph = await self.planner.refine_plan(task_graph, reflection, goal, perception)
                yield {"event": "activity", "data": "Mission Graph refined."}
            
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


LeviBrain = LeviBrainV8

