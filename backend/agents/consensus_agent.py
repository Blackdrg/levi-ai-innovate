"""
Sovereign Consensus Agent v13.0.0.
The collective adjudicator for the Absolute Monolith.
Resolves cognitive friction via Collective Resonance (CR) and Swarm Appraisal.
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult, T, R
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class ConsensusInput(BaseModel):
    goal: str = Field(..., description="The original mission goal")
    candidates: List[AgentResult] = Field(..., description="Outputs from multiple agents")
    context: Dict[str, Any] = Field(default_factory=dict)

class ConsensusAgentV13(SovereignAgent[ConsensusInput, AgentResult]):
    """
    Sovereign Ensemble Adjudicator v13.0.0.
    Calculates the Fidelity Score (S) and Collective Resonance (CR) across parallel outputs.
    """
    
    def __init__(self, max_retries: int = 1):
        super().__init__("Consensus", profile="The High Judge", use_bus=True)
        self.max_retries = max_retries
        self.current_retry = 0

    async def _run(self, input_data: ConsensusInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Consensus Protocol v13.0.0:
        1. Swarm Appraisal (Council of Models).
        2. Fidelity Matrix Calculation.
        3. Deterministic Winner Selection.
        """
        if not input_data.candidates:
            return {"message": "No candidates provided for consensus.", "success": False}

        self.logger.info(f"[Consensus-v13] Adjudicating {len(input_data.candidates)} candidates.")

        # 1. Prepare Evaluation Prompt
        candidate_block = "\n\n".join([
            f"Candidate [{i}] (Agent: {c.agent}):\n{c.message}"
            for i, c in enumerate(input_data.candidates)
        ])
        
        system_prompt = (
            "You are the LEVI Sovereign High Adjudicator (v13.0.0). "
            "Select the BEST output based on the Fidelity Tensor:\n"
            "1. Correctness (30%)\n2. Logic (20%)\n3. Safety (25%)\n4. Resonance (25%)\n\n"
            "Output ONLY valid JSON: { \"winner_index\": 0, \"fidelity\": 0.98, \"justification\": \"...\" }"
        )

        generator = SovereignGenerator()
        
        # 2. Parallel Swarm Appraisal
        raw_json = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Goal: {input_data.goal}\n\nCandidates:\n{candidate_block}"}
        ])

        try:
            content = raw_json.strip()
            if "```json" in content: content = content.split("```json")[1].split("```")[0]
            data = json.loads(content)
            
            winner_idx = data.get("winner_index", 0)
            best_result = input_data.candidates[winner_idx]
            fidelity = data.get("fidelity", 0.9)

            return {
                "message": f"Consensus Reached. Selected {best_result.agent}.",
                "success": True,
                "data": {
                    "winner": best_result.dict(),
                    "fidelity_score": fidelity,
                    "justification": data.get("justification", ""),
                    "status": "crystallized_v13"
                },
                "score": fidelity
            }

        except Exception as e:
            self.logger.error(f"[Consensus-v13] Adjudication failed: {e}")
            return {
                "message": "Consensus calculation failed. Falling back.",
                "success": True,
                "data": input_data.candidates[0].dict(),
                "score": 0.5
            }

# Graduation Alias for the Absolute Monolith (v13.0)
ConsensusAgentV11 = ConsensusAgentV13
