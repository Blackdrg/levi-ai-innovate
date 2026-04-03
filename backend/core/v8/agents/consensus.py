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
    fragility_score: float = Field(default=0.0, description="Domain fragility from tracker")

class ConsensusAgentV8(BaseV8Agent[ConsensusInput]):
    """
    LeviBrain v8.7: Swarm Consensus Engine
    Performs high-fidelity reconciliation with mood diversity and confidence weighting.
    """

    def __init__(self):
        super().__init__("ConsensusAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: ConsensusInput, context: Dict[str, Any]) -> AgentResult:
        query = input_data.input
        outputs = input_data.agent_outputs
        fragility = input_data.fragility_score
        
        self.logger.info(f"[Consensus-V8] Initiating election for swarm size {len(outputs)} (Fragility: {fragility:.2f})")

        # 1. Consensus Analysis & Conflict detection
        analysis_raw = await self._analyze_consensus(query, outputs)
        
        # 2. Extract Metrics
        conflicts = analysis_raw.get("conflicts", [])
        agreement_level = analysis_raw.get("agreement_score", 0.5) # 0.0 to 1.0
        
        # 3. High-Fidelity Reconciliation
        # If agreement is low and fragility is high, we trigger an 'Exhaustive Debate' synthesis
        strategy = "exhaustive_debate" if (agreement_level < 0.6 and fragility > 0.5) else "unified_synthesis"
        
        reconciled_response = await self._reconcile_outputs(query, outputs, conflicts, strategy)
        
        return AgentResult(
            success=True,
            message=reconciled_response,
            data={
                "swarm_size": len(outputs),
                "agreement_score": agreement_level,
                "conflicts_detected": len(conflicts),
                "strategy": strategy,
                "fragility_at_execution": fragility
            }
        )

    async def _analyze_consensus(self, query: str, outputs: Dict[str, str]) -> Dict[str, Any]:
        """Performs a structured cross-analysis of swarm outputs."""
        prompt = (
            f"MISSION OBJECTIVE: {query}\n\n"
            "SWARM OUTPUTS:\n" + "\n".join([f"[{k}]: {v[:500]}..." for k, v in outputs.items()]) + "\n\n"
            "Analyze the swarm for:\n"
            "1. Logical Intersection (shared correct points)\n"
            "2. Critical Contradictions (conflicting facts)\n"
            "3. Agreement Score (0.0: total chaos, 1.0: perfect consensus)\n\n"
            "Respond in JSON format: {'conflicts': [], 'agreement_score': 0.0}"
        )
        
        res_raw = await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Swarm Analyst. Perform a logical intersection and conflict audit."},
            {"role": "user", "content": prompt}
        ], temperature=0.2)
        
        try:
            # Clean JSON if necessary
            json_str = res_raw.strip().replace("```json", "").replace("```", "")
            return json.loads(json_str)
        except:
            self.logger.warning("[Consensus-V8] Failed to parse analysis JSON. Falling back to defaults.")
            return {"conflicts": ["Potential logical divergence detected"], "agreement_score": 0.5}

    async def _reconcile_outputs(self, query: str, outputs: Dict[str, str], conflicts: List[str], strategy: str) -> str:
        """Synthesizes the final response by resolving conflicts and merging insights."""
        context_str = "Perform an EXHAUSTIVE DEBATE reconciliation. Scrutinize every contradiction." if strategy == "exhaustive_debate" else "Synthesize a unified high-fidelity response."
        
        prompt = (
            f"QUERY: {query}\n\n"
            "SWARM FINDINGS:\n" + "\n".join([f"[{k}]: {v}" for k, v in outputs.items()]) + "\n\n"
            "RECONCILIATION TASK: " + context_str + "\n\n"
            "CONFLICTS TO RESOLVE:\n" + ("\n".join(conflicts) if conflicts else "None detected.") + "\n\n"
            "Final Response Requirements:\n"
            "- Grounded in the logical intersection of the swarm.\n"
            "- Filtered for hallucinations.\n"
            "- Unified voice."
        )
        
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Swarm Swarm Consensus (v8.7). Resolve and synthesize."},
            {"role": "user", "content": prompt}
        ], temperature=0.3)
