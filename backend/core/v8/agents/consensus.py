import logging
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class ConsensusInput(BaseModel):
    input: str = Field(..., description="Original user query")
    agent_outputs: Dict[str, str] = Field(..., description="Mapping of agent_id to their drafted response")

class ConsensusAgentV8(BaseV8Agent[ConsensusInput]):
    """
    LeviBrain v8.5: Consensus Engine (Swarm Reconciliation)
    Reconciles conflicting findings from different waves into a single source of truth.
    """

    def __init__(self):
        super().__init__("ConsensusAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: ConsensusInput, context: Dict[str, Any]) -> AgentResult:
        query = input_data.input
        outputs = input_data.agent_outputs
        
        self.logger.info(f"[Consensus-V8] Initiating swarm reconciliation for {len(outputs)} inputs.")

        # 1. Conflict Detection Pass
        conflicts = await self._detect_conflicts(query, outputs)
        
        # 2. Synthesis & Reconciliation
        reconciled_response = await self._reconcile_outputs(query, outputs, conflicts)
        
        return AgentResult(
            success=True,
            message=reconciled_response,
            data={
                "swarm_size": len(outputs),
                "conflicts_detected": len(conflicts) > 0,
                "reconciliation_strategy": "Consensus Wave"
            }
        )

    async def _detect_conflicts(self, query: str, outputs: Dict[str, str]) -> List[str]:
        """Detects logical or factual contradictions between agent outputs."""
        prompt = (
            f"User Query: {query}\n\n"
            "Agent Findings:\n" + "\n".join([f"Agent [{k}]: {v}" for k, v in outputs.items()]) + "\n\n"
            "Identify any factual or logical contradictions between these findings. If none, return 'No conflicts'."
        )
        res = await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Swarm Critic. Detect contradictions and logic gaps."},
            {"role": "user", "content": prompt}
        ])
        return [res] if "No conflicts" not in res else []

    async def _reconcile_outputs(self, query: str, outputs: Dict[str, str], conflicts: List[str]) -> str:
        """Synthesizes the final response by resolving conflicts and merging insights."""
        prompt = (
            f"User Query: {query}\n\n"
            "Draft Findings:\n" + "\n".join([f"Agent [{k}]: {v}" for k, v in outputs.items()]) + "\n\n"
            "Conflicts Identified:\n" + ("\n".join(conflicts) if conflicts else "None") + "\n\n"
            "Task: Resolve all conflicts and synthesize a single, high-fidelity response. "
            "Prioritize source grounding and logical consistency."
        )
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Swarm Consensus. Synthesize the final high-fidelity response."},
            {"role": "user", "content": prompt}
        ])
