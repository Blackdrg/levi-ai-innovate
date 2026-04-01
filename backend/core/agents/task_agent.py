"""
backend/services/orchestrator/agents/task_agent.py

Task Agent for LEVI-AI v6.8.8.
Advanced planning and step-by-step execution orchestrator.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.services.orchestrator.meta_planner import decompose_goal
from backend.services.orchestrator.orchestrator_types import IntentResult

logger = logging.getLogger(__name__)

class TaskInput(BaseModel):
    input: str = Field(..., description="The complex goal to achieve")
    user_id: str = Field(..., description="User ID for planning context")

class TaskAgent(BaseTool[TaskInput, StandardToolOutput]):
    """
    The Task Agent breaks down complex user goals into sub-tasks and delegates them.
    """
    
    name = "task_agent"
    description = "Advanced planning and step-by-step execution orchestrator."
    input_schema = TaskInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: TaskInput, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the Meta-Brain goal decomposition and formats the initial strategy.
        """
        user_id = input_data.user_id
        query = input_data.input
        
        try:
            # 1. 🔍 Decompose the goal using Meta-Brain
            # We construct a synthetic IntentResult for the planner if not already present
            intent_context = context.get("intent", IntentResult(
                intent_type="complex_task", 
                complexity_level=3, 
                confidence_score=0.9,
                estimated_cost_weight="high"
            ))
            
            strategy = await decompose_goal(query, intent_context, context)
            
            # 2. 📝 Format plan for user
            subgoals_text = "\n".join([f"- {sg.description} (Agent: {sg.target_agent})" for sg in strategy.subgoals])
            
            response = (
                f"As your specialized Task Agent, I've architected a strategy to achieve your goal.\n\n"
                f"**Overall Strategy**: {strategy.overall_strategy}\n\n"
                f"**Execution Steps**:\n{subgoals_text}\n\n"
                f"Should I proceed with the first step?"
            )
            
            return {
                "success": True,
                "message": response,
                "data": {
                    "strategy": strategy.overall_strategy,
                    "subgoal_count": len(strategy.subgoals),
                    "model_recommended": strategy.recommended_model
                },
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"[TaskAgent] failure: {e}")
            return {
                "success": False,
                "error": f"Task Architect encountered a barrier: {str(e)}",
                "agent": self.name
            }
