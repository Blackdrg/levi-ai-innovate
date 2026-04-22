# backend/agents/shadow.py
import logging
from typing import Dict, Any, List
from backend.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)

class ShadowAgent(BaseAgent):
    """
    Sovereign Shadow: Redundancy.
    """

    def __init__(self):
        super().__init__(
            agent_id="shadow_agent",
            name="Shadow",
            role="Redundancy",
            goal="Detect silent execution errors through redundant computation."
        )

    async def _run(self, input_data: AgentInput) -> AgentOutput:
        """
        Sovereign v22.1: Redundant Execution Logic.
        Spawns a secondary 'Shadow' pass of the mission to detect divergent results.
        """
        from backend.utils.llm_utils import call_heavyweight_llm
        import difflib
        
        objective = input_data.objective
        primary_output = input_data.context.get("primary_output", "")
        
        logger.info(f"🌑 [Shadow] Performing redundant execution for mission: {objective[:50]}...")
        
        # 1. Secondary Execution Pass
        shadow_prompt = (
            "You are the LEVI Shadow Executor. Perform a redundant pass of the following objective.\n"
            f"OBJECTIVE: {objective}\n\n"
            "Produce the definitive output. If this is a coding task, provide the full code."
        )
        
        shadow_output = await call_heavyweight_llm([{"role": "user", "content": shadow_prompt}])
        
        # 2. Divergence Analysis
        similarity = difflib.SequenceMatcher(None, primary_output, shadow_output).ratio()
        
        divergence_detected = similarity < 0.85
        
        if divergence_detected:
            logger.warning(f"🚨 [Shadow] SILENT ERROR DETECTED! Similarity: {similarity:.2f}")
            return AgentOutput(
                agent_id=self.agent_id,
                success=False,
                output="Redundancy check FAILED. Significant divergence detected between primary and shadow execution.",
                data={
                    "similarity": similarity,
                    "shadow_output": shadow_output,
                    "divergence_score": 1.0 - similarity
                }
            )
        
        logger.info(f"✅ [Shadow] Redundancy check PASSED. Similarity: {similarity:.2f}")
        return AgentOutput(
            agent_id=self.agent_id,
            success=True,
            output=f"Shadow verification passed (Similarity: {similarity:.2f}).",
            data={
                "similarity": similarity,
                "status": "AxiomVerified"
            }
        )
