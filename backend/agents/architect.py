# backend/agents/architect.py
import logging
import json
from typing import Dict, Any, List
from backend.agents.base import BaseAgent, AgentInput, AgentOutput
from backend.utils.llm_utils import call_heavyweight_llm

logger = logging.getLogger(__name__)

class ArchitectAgent(BaseAgent):
    """
    Sovereign Architect: The DAG Designer.
    Decomposes complex goals into multi-wave Directed Acyclic Graphs (DAGs).
    """

    def __init__(self):
        super().__init__(
            agent_id="architect_agent",
            name="Architect",
            role="Goal Decomposition",
            goal="Design high-efficiency cognitive execution paths."
        )

    async def _run(self, input_data: AgentInput) -> AgentOutput:
        """Decomposes a goal into a series of task waves."""
        goal = input_data.objective
        available_agents = input_data.context.get("agents", [])
        
        logger.info(f"🏗️ [Architect] Designing DAG for goal: {goal}")
        
        # 1. Generate DAG Structure
        prompt = (
            "You are the LEVI Architect. Decompose the following goal into a multi-wave DAG.\n"
            f"GOAL: {goal}\n"
            f"AVAILABLE AGENTS: {', '.join(available_agents)}\n\n"
            "Format the output as a LIST of waves, where each wave is a list of tasks.\n"
            "Example: [[{\"agent\": \"Scout\", \"task\": \"...\"}], [{\"agent\": \"Artisan\", \"task\": \"...\"}]]"
        )
        
        dag_res = await call_heavyweight_llm([{"role": "user", "content": prompt}])
        
        # 2. Extract JSON DAG
        import re
        json_match = re.search(r"\[.*\]", dag_res, re.DOTALL)
        dag = json.loads(json_match.group()) if json_match else []
        
        return AgentOutput(
            agent_id=self.agent_id,
            success=True,
            output=f"DAG designed with {len(dag)} waves.",
            data={"dag": dag}
        )
