import logging
import re
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class CriticInput(BaseModel):
    goal: str = Field(..., description="The original goal of the task")
    success_criteria: List[str] = Field(default_factory=list)
    response: str = Field(..., description="The output produced by another agent")
    user_input: str = Field(default="", description="Original user prompt")

class CriticAgentV8(BaseV8Agent[CriticInput]):
    """
    LeviBrain v8: Critic & Validator System
    Multi-metric scoring + Hallucination check + Fix derivation
    """

    def __init__(self):
        super().__init__("CriticAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: CriticInput, context: Dict[str, Any]) -> AgentResult:
        self.logger.info(f"[Critic-V8] Initiating high-fidelity audit for goal: {input_data.goal[:30]}")

        # 1. Multi-metric Analysis pass (Alignment, Grounding, Resonance)
        metrics = await self._analyze_quality(input_data)
        
        # 2. Hallucination & Alignment pass
        alignment = await self._check_alignment(input_data)
        
        # 3. Unified Fidelity Formula: (Coherence * Grounding) / Perplexity
        # Mapped to: (alignment * grounding) / (1.1 - resonance)
        alignment_score = metrics.get("alignment", 0.5)
        grounding_score = metrics.get("grounding", 0.5)
        resonance_score = metrics.get("resonance", 0.5)
        is_safe = alignment.get("is_safe", False)
        
        fidelity = (alignment_score * grounding_score) / (1.1 - resonance_score)
        fidelity = max(0.0, min(1.0, fidelity))
        
        # A mission is successful only if fidelity is high AND alignment is safe
        success = fidelity >= 0.85 and is_safe
        
        return AgentResult(
            success=success,
            message=f"Sovereign Audit Complete: {int(fidelity*100)}% Fidelity.",
            data={
                "fidelity_score": round(fidelity, 4),
                "is_satisfactory": success,
                "issues": metrics.get("issues", []),
                "fix": metrics.get("fix", "No fix required."),
                "hallucination_detected": not is_safe,
                "metrics": {
                    "alignment": alignment_score,
                    "grounding": grounding_score,
                    "resonance": resonance_score
                }
            }
        )

    async def _analyze_quality(self, input_data: CriticInput) -> Dict[str, Any]:
        """Quality analysis pass: Alignment, Grounding, Resonance."""
        prompt = (
            f"GOAL: {input_data.goal}\n"
            f"CRITERIA: {input_data.success_criteria}\n"
            f"DRAFT: {input_data.response}\n\n"
            "Evaluate this output against the mission goal. Score 0.0-1.0 for:\n"
            "1. Alignment (Logical consistency with goal)\n"
            "2. Grounding (Factual accuracy and source relevance)\n"
            "3. Resonance (Tone, style, and user alignment)\n\n"
            "Return JSON: {\"quality_score\": 0.9, \"alignment\": 0.95, \"grounding\": 0.9, \"resonance\": 0.85, \"issues\": [\"...\"], \"fix\": \"...\"}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI High-Fidelity Auditor."},
                {"role": "user", "content": prompt}
            ])
            import json as json_lib
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                 return json_lib.loads(json_match.group(0))
        except Exception as e:
            self.logger.warning(f"Quality analysis failed: {e}")
            
        return {"quality_score": 0.5, "issues": ["High-fidelity analysis pass failed."], "fix": "Retry mission with higher reasoning depth."}

    async def _check_alignment(self, input_data: CriticInput) -> Dict[str, Any]:
        """Hallucination and Alignment pass."""
        prompt = (
            f"USER INPUT: {input_data.user_input}\n"
            f"DRAFT RESPONSE: {input_data.response}\n\n"
            "Audit for hallucination or non-aligned info? (true/false)\n"
            "Return JSON: {\"is_safe\": true, \"reason\": \"...\"}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Alignment Officer."},
                {"role": "user", "content": prompt}
            ])
            import json as json_lib
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                 return json_lib.loads(json_match.group(0))
        except Exception as e:
             self.logger.warning(f"Alignment check failed: {e}")
             
        return {"is_safe": False, "reason": "Check interrupted."}
