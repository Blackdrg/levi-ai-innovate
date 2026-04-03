import os
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .orchestrator_types import ToolResult
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    Sovereign Workflow Engine v8.
    Executes multi-step autonomous loops until goals are achieved.
    Configurable via LEVI_WORKFLOW_MAX_ITERATIONS (default 5).
    """

    def __init__(self):
        self.max_iterations = int(os.getenv("LEVI_WORKFLOW_MAX_ITERATIONS", 5))

    async def run(self, initial_goal: Any, brain: Any, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main autonomous execution loop.
        Architecture: Plan -> Execute -> Evaluate -> Refine -> Repeat.
        """
        user_id = perception.get("user_id", "guest")
        request_id = f"wf_{uuid.uuid4().hex[:8]}"
        
        state = {
            "request_id": request_id,
            "goal": initial_goal.objective,
            "iterations": 0,
            "steps": [],
            "final_output": None,
            "success": False
        }

        current_goal = initial_goal
        
        logger.info(f"[WorkflowEngine] Starting autonomous session: {request_id} (Max iterations: {self.max_iterations})")

        for i in range(self.max_iterations):
            state["iterations"] = i + 1
            logger.info(f"[WorkflowEngine] Iteration {i+1}/{self.max_iterations} for goal: {current_goal.objective}")
            
            # 1. Planning
            task_graph = await brain.planner.build_task_graph(current_goal, perception)
            
            # 2. Execution
            results = await brain.executor.execute(task_graph, perception, user_id=user_id)
            state["steps"].append({
                "iteration": i + 1,
                "goal": current_goal.objective,
                "results": [r.dict() for r in results]
            })

            # 3. Synthesis of intermediate response
            from .engine import synthesize_response
            draft_response = await synthesize_response(results, perception.get("context", {}))

            # 4. Evaluation (is the mission accomplished?)
            reflection = await brain.reflection.evaluate(draft_response, current_goal, perception, results)
            
            if reflection["is_satisfactory"]:
                logger.info(f"[WorkflowEngine] Goal accomplished in {i+1} iterations.")
                state["final_output"] = draft_response
                state["success"] = True
                break
                
            if i == self.max_iterations - 1:
                logger.warning("[WorkflowEngine] Max iterations reached. Returning best effort.")
                state["final_output"] = draft_response
                break

            # 5. Goal Refinement (Auto-correction)
            logger.info(f"[WorkflowEngine] Refinement required: {reflection.get('issues', ['Unknown issue'])}")
            current_goal = await self.refine_goal(current_goal, reflection, draft_response)
            
        return state

    async def refine_goal(self, current_goal: Any, reflection: Dict[str, Any], last_output: str) -> Any:
        """Evolves the mission goal based on feedback/failures using Sovereign Reasoning."""
        from backend.engines.chat.generation import SovereignGenerator
        
        refine_prompt = (
            f"Current Goal: {current_goal.objective}\n"
            f"Last Output: {last_output}\n"
            f"Critic Issues: {', '.join(reflection.get('issues', []))}\n\n"
            "Synthesize a revised, high-fidelity objective for the next cognitive iteration "
            "to resolve the issues and achieve the mission goal."
        )
        
        generator = SovereignGenerator()
        new_objective = await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Mission Architect."},
            {"role": "user", "content": refine_prompt}
        ])
        
        current_goal.objective = new_objective.strip()
        return current_goal

    def is_goal_complete(self, results: List[ToolResult], goal: Any) -> bool:
        """Determines if the terminal nodes of the mission achieved success."""
        return all(r.success for r in results)
