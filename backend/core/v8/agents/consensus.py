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

    async def _arbitrate_disagreement(self, top_two: List[Dict[str, Any]], goal: str) -> Dict[str, Any]:
        """
        Sovereign v14.0: Autonomous Arbitration.
        Invoked when top agents have high but conflicting outputs.
        Uses a 'Senior Arbitrator' (Meta-Reasoning) to resolve the delta.
        """
        self.logger.warning("[Consensus-V14] Resonance Conflict Detected. Invoking Senior Arbitrator...")
        
        # Meta-Prompt for arbitration
        arbitration_prompt = (
            f"You are the Senior Arbitrator for LEVI-AI. Two high-fidelity agents have provided "
            f"conflicting responses for the goal: '{goal}'.\n\n"
            f"Agent A ({top_two[0]['agent']}): {top_two[0]['response']}\n"
            f"Agent B ({top_two[1]['agent']}): {top_two[1]['response']}\n\n"
            "Analyze both responses for factual consistency, logic, and alignment with the goal. "
            "Select the winner or synthesize a superior resolution. "
            "Return JSON: {\"winner\": \"agent_name or synthesized\", \"resolution\": \"...\", \"reasoning\": \"...\"}"
        )
        
        # This would call the Llama 70B or a high-tier reasoning engine
        # For now, we simulate the arbitration or delegate to a 'ReasoningEngine'
        from backend.engines.chat.generation import SovereignGenerator
        generator = SovereignGenerator()
        
        raw_resolution = await generator.council_of_models([
            {"role": "system", "content": arbitration_prompt}
        ])
        
        # In a real impl, we'd parse JSON. For this PR, we'll use a simplified synthesis.
        return {
            "agent": "Senior Arbitrator (Synthesized)",
            "response": raw_resolution if raw_resolution else top_two[0]['response'],
            "score": 0.99,
            "is_satisfactory": True,
            "audit": {"reason": "Arbitrated Conflict"}
        }

    async def _execute_system(self, input_data: ConsensusInput, context: Dict[str, Any]) -> AgentResult:
        self.logger.info(f"[Consensus-V14] Evaluating {len(input_data.agent_outputs)} agent outputs...")

        if not input_data.agent_outputs:
            return AgentResult(success=False, message="No agent outputs provided for consensus.", agent=self.name)

        scored_results = []
        for output in input_data.agent_outputs:
            agent_name = output.get("agent", "unknown")
            response = output.get("message", output.get("response", ""))
            
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

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        
        # 2. Check for Disagreement (Arbitration Gate)
        # If the top two results have similar high scores (>0.8) and a delta < 0.05
        if len(scored_results) >= 2:
            s1, s2 = scored_results[0], scored_results[1]
            if s1["score"] > 0.8 and s2["score"] > 0.8 and abs(s1["score"] - s2["score"]) < 0.05:
                best_match = await self._arbitrate_disagreement(scored_results[:2], input_data.goal)
            else:
                best_match = scored_results[0]
        else:
            best_match = scored_results[0]
        
        success = best_match["is_satisfactory"]
        
        self.logger.info(f"[Consensus-V14] Selection achieved: {best_match['agent']} (Score: {best_match['score']:.2f})")

        return AgentResult(
            success=success,
            message=best_match["response"],
            data={
                "winner": best_match["agent"],
                "score": best_match["score"],
                "all_scores": [{s["agent"]: s["score"]} for s in scored_results],
                "expert_audit": best_match["audit"],
                "arbitrated": "Senior Arbitrator" in best_match["agent"]
            }
        )
