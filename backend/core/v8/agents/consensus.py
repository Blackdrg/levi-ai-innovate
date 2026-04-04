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
    LeviBrain v9.5: Swarm Consensus Engine 2.0
    Performs high-fidelity reconciliation with multi-model voting and confidence weighting.
    """

    def __init__(self):
        super().__init__("ConsensusAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: ConsensusInput, context: Dict[str, Any]) -> AgentResult:
        query = input_data.input
        outputs = input_data.agent_outputs
        fragility = input_data.fragility_score
        
        self.logger.info(f"[Consensus-V9.5] Initiating Swarm Election (Size: {len(outputs)}, Fragility: {fragility:.2f})")

        # 1. Consensus Analysis & Intersection Detection
        analysis_raw = await self._analyze_consensus(query, outputs)
        
        # 2. Extract Metrics & Weighted Confidence
        conflicts = analysis_raw.get("conflicts", [])
        agreement_level = analysis_raw.get("agreement_score", 0.5)
        # v9.5: Confidence weighting based on fragility and swarm density
        weighted_confidence = agreement_level * (1.0 - (fragility * 0.5))

        # 3. Dynamic Strategy Selection
        if weighted_confidence < 0.4:
            strategy = "adversarial_audit" # Highest rigor for high-risk divergence
        elif agreement_level < 0.7:
            strategy = "exhaustive_debate"
        else:
            strategy = "unified_synthesis"
            
        self.logger.info(f"[Consensus-V9.5] Strategy: {strategy} (Confidence: {weighted_confidence:.2f})")

        # 4. Multi-Model Synthesis Wave
        reconciled_response = await self._reconcile_outputs(query, outputs, conflicts, strategy)
        
        return AgentResult(
            success=True,
            message=reconciled_response,
            data={
                "swarm_size": len(outputs),
                "agreement_score": agreement_level,
                "weighted_confidence": weighted_confidence,
                "conflicts_detected": len(conflicts),
                "strategy": strategy,
                "v9_status": "synced"
            }
        )

    async def _analyze_consensus(self, query: str, outputs: Dict[str, str]) -> Dict[str, Any]:
        """Performs a deep logical audit of swarm outputs."""
        prompt = (
            f"MISSION: {query}\n\n"
            "SWARM AGENT OUTPUTS:\n" + "\n".join([f"[{k}]: {v[:800]}..." for k, v in outputs.items()]) + "\n\n"
            "LEVI CONSENSUS v2.0 AUDIT:\n"
            "1. Identify the 'CORE TRUTH' (points agreed upon by >70% of the swarm).\n"
            "2. Identify 'CRITICAL DIVERGENCE' (conflicting facts or logic).\n"
            "3. Score the Agreement (0.0 to 1.0).\n\n"
            "Respond ONLY with a JSON object: {'conflicts': [], 'agreement_score': 0.0, 'core_truth': ''}"
        )
        
        res_raw = await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Swarm Election Auditor. Detect logical divergence."},
            {"role": "user", "content": prompt}
        ], temperature=0.1)
        
        try:
            import json
            json_str = res_raw.strip().replace("```json", "").replace("```", "")
            return json.loads(json_str)
        except:
            return {"conflicts": ["High-risk logical divergence"], "agreement_score": 0.4}

    async def _reconcile_outputs(self, query: str, outputs: Dict[str, str], conflicts: List[str], strategy: str) -> str:
        """Synthesizes the final high-fidelity response."""
        rigor_map = {
            "adversarial_audit": "Perform an ADVERSARIAL audit. Challenge every assertion.",
            "exhaustive_debate": "Examine every contradiction with scientific rigor.",
            "unified_synthesis": "Merge insights into a single high-fidelity response."
        }
        
        prompt = (
            f"QUERY: {query}\n\n"
            "SWARM INPUTS:\n" + "\n".join([f"[{k}]: {v}" for k, v in outputs.items()]) + "\n\n"
            "RECONCILIATION STRATEGY: " + rigor_map.get(strategy, "Standard Synthesis") + "\n\n"
            "DIVERGENCE LOG:\n" + ("\n".join(conflicts) if conflicts else "None.") + "\n\n"
            "OUTPUT REQUIREMENTS:\n"
            "- Filter for systemic bias.\n"
            "- Maximize information density.\n"
            "- Finality and clarity."
        )
        
        return await self.generator.council_of_models([
            {"role": "system", "content": f"You are the LEVI Swarm Consensus Controller {strategy.upper()}. Finalize the mission."},
            {"role": "user", "content": prompt}
        ], temperature=0.2)
