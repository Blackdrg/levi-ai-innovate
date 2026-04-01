"""
backend/services/orchestrator/agents/critic_agent.py

LEVI v6: The Role-Based Validator.
Reviews previous agent outputs for quality, resonance, and accuracy.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.generation import _async_call_llm_api

logger = logging.getLogger(__name__)

class CriticInput(BaseModel):
    goal: str = Field(..., description="The original goal being achieved")
    agent_output: str = Field(..., description="The output to evaluate")
    context: Dict[str, Any] = Field(default_factory=dict)

class CriticAgent(BaseTool[CriticInput, StandardToolOutput]):
    """
    Role: High-level validator (The Critic).
    Returns a structured score (0-1.0). If score < 0.7, triggers reflection.
    """
    name = "critic_agent"
    description = "Role: Formal Validator. Reviews outputs for quality, accuracy, and philosophical depth."
    input_schema = CriticInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: ValidatorInput, context: Dict[str, Any]) -> Dict[str, Any]:
        request_id = context.get("request_id", "external")
        logger.info(f"[{request_id}] [Validator] Scoring autonomous output quality...")
        
        system_prompt = (
            "You are the LEVI Validator. Analyze the agent's output against the goal.\n"
            "Criteria:\n"
            "1. Accuracy: Is the information correct?\n"
            "2. Resonance: Does it match the philosophical, anti-cliché tone of LEVI?\n"
            "3. Completeness: Does it fully address the goal?\n\n"
            "Output ONLY JSON:\n"
            "{\n"
            "  \"quality_score\": 0.95,\n"
            "  \"critique_items\": [\"Suggestion 1\", \"Suggestion 2\"],\n"
            "  \"reasoning\": \"Brief explanation of the score.\"\n"
            "}"
        )
        
        raw_response = await _async_call_llm_api(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Goal: {input_data.goal}\nOutput: {input_data.agent_output}"}
            ],
            model="llama-3.1-70b-versatile",
            temperature=0.1,
            request_id=request_id
        )
        
        try:
            # Simple JSON extraction
            content = raw_response.strip()
            if "```json" in content: content = content.split("```json")[1].split("```")[0]
            elif "```" in content: content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content)
            score = data.get("quality_score", 0.5)
            critique = data.get("critique_items", [])
            success = score >= 0.70 # v6 Hardening Threshold

            return {
                "success": success,
                "message": f"Validation complete (Score: {score})",
                "data": {
                    "quality_score": score,
                    "critique": ". ".join(critique) if critique else None,
                    "reasoning": data.get("reasoning", "")
                },
                "agent": self.name
            }
        except Exception as e:
            logger.error(f"[Validator] JSON Parse Error: {e}")
            return {
                "success": False,
                "error": "Validation failed to generate structured score.",
                "agent": self.name
            }
