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
from backend.utils.validators import DeterministicValidator
from backend.utils.grounding import FactualGroundingHub

logger = logging.getLogger(__name__)

class FidelityRubric(BaseModel):
    """
    Objective scoring dimensions for the Swarm Adjudication Protocol (v1.0.0-RC1).
    """
    syntax_correctness: float = Field(0.0, ge=0.0, le=1.0)
    logical_consistency: float = Field(0.0, ge=0.0, le=1.0)
    factual_grounding: float = Field(0.0, ge=0.0, le=1.0)
    sovereign_resonance: float = Field(0.0, ge=0.0, le=1.0)

    def calculate_fidelity(self, content: str, intent: str = "general") -> float:
        """
        v1.0.0-RC1: Deterministic Weighted Aggregator.
        Combines neural scores with a hard-coded DeterministicValidator [40% weight].
        """
        weights = self.get_weight_profile(intent)
        det_scores = DeterministicValidator.validate(content, intent)

        # Synthesis: LLM-Appraisal (60%) + DeterministicTruth (40%)
        final_syntax = (self.syntax_correctness * 0.6) + (det_scores["syntax"] * 0.4)
        final_logic = (self.logical_consistency * 0.6) + (det_scores["logic"] * 0.4)
        final_grounding = (self.factual_grounding * 0.6) + (det_scores["grounding"] * 0.4)
        final_resonance = (self.sovereign_resonance * 0.6) + (det_scores["resonance"] * 0.4)

        return (
            (final_syntax * weights["syntax"]) +
            (final_logic * weights["logic"]) +
            (final_grounding * weights["grounding"]) +
            (final_resonance * weights["resonance"])
        )

    @staticmethod
    def get_weight_profile(intent: str) -> Dict[str, float]:
        """Returns the specific weight distribution for a given mission intent."""
        profiles = {
            "code": {"syntax": 0.5, "logic": 0.3, "grounding": 0.1, "resonance": 0.1},
            "research": {"syntax": 0.1, "logic": 0.2, "grounding": 0.5, "resonance": 0.2},
            "analysis": {"syntax": 0.1, "logic": 0.5, "grounding": 0.2, "resonance": 0.2},
            "general": {"syntax": 0.3, "logic": 0.3, "grounding": 0.2, "resonance": 0.2}
        }
        return profiles.get(intent, profiles["general"])

class ConsensusInput(BaseModel):
    goal: str = Field(..., description="The original mission goal")
    candidates: List[AgentResult] = Field(..., description="Outputs from multiple agents")
    rubrics: Optional[List[FidelityRubric]] = Field(None, description="Objective metrics from each agent")
    context: Dict[str, Any] = Field(default_factory=dict)

class ConsensusAgentV13(SovereignAgent[ConsensusInput, AgentResult]):
    """
    Sovereign Ensemble Adjudicator v13.1.0.
    Calculates the Fidelity Score (S) and Collective Resonance (CR) across parallel outputs.
    """
    
    def __init__(self, max_retries: int = 1):
        super().__init__("Consensus", profile="The High Judge", use_bus=True)
        self.max_retries = max_retries

    async def _run(self, input_data: ConsensusInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Consensus Protocol v13.1.0:
        1. Objective Rubric Aggregation.
        2. Swarm appraisal via Council of Models.
        3. Deterministic Winner Selection.
        """
        if not input_data.candidates:
            return {"message": "No candidates provided for consensus.", "success": False}

        self.logger.info(f"[Consensus-v13.1] Adjudicating {len(input_data.candidates)} candidates.")

        # 1. Prepare Deterministic Analysis
        intent = input_data.context.get("intent", "general")
        rubric_summaries = ""
        if input_data.rubrics:
            for i, r in enumerate(input_data.rubrics):
                # Now passing content to include DeterministicValidator
                obj_score = r.calculate_fidelity(input_data.candidates[i].message, intent)
                rubric_summaries += f"Candidate [{i}] Ground-Truth Score: {obj_score:.2f}\n"

        # 2. Prepare Evaluation Prompt
        candidate_block = "\n\n".join([
            f"Candidate [{i}] (Agent: {c.agent}):\n{c.message}"
            for i, c in enumerate(input_data.candidates)
        ])
        
        system_prompt = (
            "You are the LEVI Sovereign High Adjudicator (v13.1.0). "
            "Select the BEST output by synthesizing objective rubric data with neural appraisal.\n"
            "Formal Rubric:\n1. Correctness (30%)\n2. Logic (30%)\n3. Factual Grounding (20%)\n4. Resonance (20%)\n\n"
            "Output ONLY valid JSON: { \"winner_index\": 0, \"fidelity\": 0.98, \"justification\": \"...\" }"
        )

        generator = SovereignGenerator()
        
        # 3. Parallel Swarm Appraisal
        user_content = f"Goal: {input_data.goal}\n\nObjective Inputs:\n{rubric_summaries}\n\nCandidates:\n{candidate_block}"
        raw_json = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ])

        try:
            content = raw_json.strip()
            if "```json" in content: content = content.split("```json")[1].split("```")[0]
            data = json.loads(content)
            
            winner_idx = data.get("winner_index", 0)
            best_result = input_data.candidates[winner_idx]
            
            # Weighted synthesis of Council appraisal and Ground-Truth score
            candidate_fidelity = data.get("fidelity", 0.9)
            if input_data.rubrics and winner_idx < len(input_data.rubrics):
                obj_score = input_data.rubrics[winner_idx].calculate_fidelity(best_result.message, intent)
                final_fidelity = (candidate_fidelity * 0.6) + (obj_score * 0.4)
            else:
                final_fidelity = candidate_fidelity

            # 4. Factual Grounding (Audit Point 09)
            # Perform a final knowledge resonance check on the winner's claims
            user_id = input_data.context.get("user_id", "global")
            grounding_res = await FactualGroundingHub.verify_claims(user_id, [best_result.message[:200]]) # Simplified claim extraction
            
            if not grounding_res["is_grounded"]:
                self.logger.warning(f"[Consensus-v13.1] Winner '{best_result.agent}' failed grounding check ({grounding_res['grounding_score']}). Penalizing fidelity.")
                final_fidelity *= grounding_res["grounding_score"]

            return {
                "message": f"Consensus Reached. Selected {best_result.agent}.",
                "success": True,
                "data": {
                    "winner": best_result.dict(),
                    "fidelity_score": final_fidelity,
                    "justification": data.get("justification", ""),
                    "grounding_report": grounding_res,
                    "status": "crystallized_v13_1"
                },
                "score": final_fidelity
            }

        except Exception as e:
            self.logger.error(f"[Consensus-v13.1] Adjudication failed: {e}")
            fallback_score = input_data.rubrics[0].calculate_fidelity() if input_data.rubrics else 0.5
            return {
                "message": "Consensus calculation failed. Falling back.",
                "success": True,
                "data": input_data.candidates[0].dict(),
                "score": fallback_score
            }

# Graduation Alias for the Absolute Monolith (v13.0)
ConsensusAgentV11 = ConsensusAgentV13
