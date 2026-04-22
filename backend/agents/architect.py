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
        
        # 1. Generate DAG Structure with Axiom 29.2
        axiom = (
            "Complexity is the enemy of truth. Decompose every user mission into the smallest possible set of "
            "independent, verifiable nodes. Ensure that the resulting Directed Acyclic Graph (DAG) maximizes "
            "parallel execution while strictly respecting causal dependencies."
        )
        
        prompt = (
            f"SYSTEM AXIOM: {axiom}\n\n"
            "You are the LEVI Architect. Decompose the following goal into a multi-wave DAG.\n"
            f"GOAL: {goal}\n"
            f"AVAILABLE AGENTS: {', '.join(available_agents)}\n\n"
            "CRITICAL-PATH HEURISTIC (Section 83.1):\n"
            "Priority(T_i) = Complexity(T_i) + Σ Latency(Children(T_i)).\n\n"
            "Format the output as a JSON object containing a LIST of 'waves', where each wave is a list of tasks. "
            "Each task MUST have 'agent', 'task', 'dependencies' (list of task indices), and 'estimated_latency_ms'.\n"
            "Example:\n"
            "{\n"
            "  \"waves\": [\n"
            "    [{\"id\": 0, \"agent\": \"Scout\", \"task\": \"...\", \"dependencies\": [], \"estimated_latency_ms\": 200}],\n"
            "    [{\"id\": 1, \"agent\": \"Artisan\", \"task\": \"...\", \"dependencies\": [0], \"estimated_latency_ms\": 500}]\n"
            "  ]\n"
            "}"
        )
        
        dag_res = await call_heavyweight_llm([{"role": "user", "content": prompt}])
        
        # 2. Extract JSON DAG
        import re
        json_match = re.search(r"\{.*\}", dag_res, re.DOTALL)
        try:
            dag_data = json.loads(json_match.group()) if json_match else {"waves": []}
            waves = dag_data.get("waves", [])
        except Exception as e:
            logger.error(f"Failed to parse Architect DAG: {e}")
            waves = []
        
        return AgentOutput(
            agent_id=self.agent_id,
            success=True,
            output=f"DAG designed with {len(waves)} waves.",
            data={"dag": waves}
        )
