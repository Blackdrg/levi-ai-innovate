import logging
import json
import re
from typing import Dict, Any, List, Optional
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
        self.logger.info(f"[Critic-V8] starting system operation for goal: {input_data.goal[:30]}")

        # 1. Multi-metric Analysis pass
        metrics = await self._analyze_quality(input_data)
        
        # 2. Hallucination & Alignment pass
        alignment = await self._check_alignment(input_data)
        
        # 3. Final synthesis of metric data
        quality_score = metrics.get("quality_score", 0.5)
        is_safe = alignment.get("is_safe", False)
        
        success = quality_score >= 0.85 and is_safe
        
        return AgentResult(
            success=success,
            message=f"Critique Pass: {int(quality_score*100)}% quality.",
            data={
                "quality_score": quality_score,
                "issues": metrics.get("issues", []),
                "fix": metrics.get("fix", "No fix required."),
                "hallucination_detected": not is_safe,
                "metrics": metrics
            }
        )

    async def _analyze_quality(self, input_data: CriticInput) -> Dict[str, Any]:
        """Quality analysis pass."""
        prompt = (
            f"Goal: {input_data.goal}\n"
            f"Success Criteria: {input_data.success_criteria}\n"
            f"Draft Response: {input_data.response}\n\n"
            "Analyze this output. Score 0.0 to 1.0.\n"
            "Return JSON: {\"quality_score\": 0.9, \"issues\": [\"...\"], \"fix\": \"...\"}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Qualitative Analyst."},
                {"role": "user", "content": prompt}
            ])
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                 return json.loads(json_match.group(0))
        except Exception as e:
            self.logger.warning(f"Quality analysis failed: {e}")
            
        return {"quality_score": 0.5, "issues": ["Analysis failed."], "fix": "Retry."}

    async def _check_alignment(self, input_data: CriticInput) -> Dict[str, Any]:
        """Hallucination and Alignment pass."""
        prompt = (
            f"Input: {input_data.user_input}\n"
            f"Response: {input_data.response}\n\n"
            "Does the response contain hallucinations or non-aligned info? (true/false)\n"
            "Return JSON: {\"is_safe\": true, \"reason\": \"...\"}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Alignment Officer."},
                {"role": "user", "content": prompt}
            ])
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                 return json.loads(json_match.group(0))
        except Exception as e:
             self.logger.warning(f"Alignment check failed: {e}")
             
        return {"is_safe": False, "reason": "Check interrupted."}
