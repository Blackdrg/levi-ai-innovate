import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from .critic import CriticAgentV8, CriticInput

logger = logging.getLogger(__name__)

class ConsensusInput(BaseModel):
    goal: str = Field(..., description="The mission goal")
    agent_outputs: List[Dict[str, Any]] = Field(..., description="Parallel outputs from multiple agents")
    user_input: str = Field(default="", description="Original user prompt")

class ConsensusAgentV8(BaseV8Agent[ConsensusInput]):
    """
    Sovereign v9.8.1: Swarm Consensus System.
    Orchestrates Expert Review across multiple agent outputs to find the highest-fidelity resonance.
    """

    def __init__(self):
        super().__init__("ConsensusAgentV8")
        self.critic = CriticAgentV8()

    async def _execute_system(self, input_data: ConsensusInput, context: Dict[str, Any]) -> AgentResult:
        self.logger.info(f"[Consensus-V8] Evaluating {len(input_data.agent_outputs)} agent outputs...")

        if not input_data.agent_outputs:
            return AgentResult(success=False, message="No agent outputs provided for consensus.", agent=self.name)

        scored_results = []
        for output in input_data.agent_outputs:
            agent_name = output.get("agent", "unknown")
            # AgentResult might have data.message or be a ToolResult
            response = output.get("message", output.get("response", ""))
            
            # 1. Expert Review Pass via CriticAgent
            critic_input = CriticInput(
                goal=input_data.goal,
                response=response,
                user_input=input_data.user_input
            )
            audit_result = await self.critic.run(critic_input, context)
            
            score = audit_result.data.get("quality_score", 0.0)
            is_satisfactory = audit_result.success
            
            scored_results.append({
                "agent": agent_name,
                "response": response,
                "score": score,
                "is_satisfactory": is_satisfactory,
                "audit": audit_result.data
            })

        # 2. Select Highest Fidelity Resonance
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        best_match = scored_results[0]
        
        success = best_match["is_satisfactory"]
        
        self.logger.info(f"[Consensus-V8] Selection achieved: {best_match['agent']} (Score: {best_match['score']:.2f})")

        return AgentResult(
            success=success,
            message=best_match["response"],
            data={
                "winner": best_match["agent"],
                "score": best_match["score"],
                "all_scores": [{s["agent"]: s["score"]} for s in scored_results],
                "expert_audit": best_match["audit"]
            }
        )
