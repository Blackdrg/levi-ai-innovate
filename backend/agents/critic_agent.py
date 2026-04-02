"""
Sovereign Critic Agent v8.
Performs recursive self-correction and rigorous alignment scoring.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class CriticInput(BaseModel):
    goal: str = Field(..., description="The original goal of the task")
    agent_output: str = Field(..., description="The output produced by another agent")
    context: Dict[str, Any] = Field(default_factory=dict)

class CriticAgent(SovereignAgent[CriticInput, AgentResult]):
    """
    Sovereign Critic & Validator.
    Validates AI outputs for accuracy, tone, and completeness.
    """
    
    def __init__(self):
        super().__init__("Critic")

    async def _run(self, input_data: CriticInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Critique Protocol v8:
        1. Multi-Dimensional Quality Analysis.
        2. Hallucination Detection.
        3. Score-based self-correction trigger.
        """
        self.logger.info(f"Critiquing Output: {input_data.goal[:40]}")
        
        system_prompt = (
            "You are the LEVI Sovereign Critic. Your role is to validate AI outputs for quality and accuracy.\n"
            "Evaluation Criteria:\n"
            "1. Accuracy: Is the information factual and derived correctly?\n"
            "2. Tone: Does it match the philosophical, anti-cliché LEVI persona?\n"
            "3. Completeness: Does it address the user goal fully?\n\n"
            "Output ONLY valid JSON:\n"
            "{\n"
            "  \"score\": 0.95,\n"
            "  \"critique\": [\"Point 1\", \"Point 2\"],\n"
            "  \"hallucination_check\": \"pass\",\n"
            "  \"remedy\": \"Suggestion to fix if applicable.\"\n"
            "}"
        )
        
        generator = SovereignGenerator()
        
        raw_json = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Goal: {input_data.goal}\n\nOutput to validate: {input_data.agent_output}"}
        ])
        
        try:
            content = raw_json.strip()
            if "```json" in content: content = content.split("```json")[1].split("```")[0]
            elif "```" in content: content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content)
            score = float(data.get("score", 0.5))
            hallucination = data.get("hallucination_check", "fail")
            
            success = score >= 0.8 and hallucination == "pass"

            return {
                "message": f"Validation Pulse: {int(score*100)}% Confidence. Hallucination: {hallucination}.",
                "success": success,
                "data": {
                    "score": score,
                    "critique": data.get("critique", []),
                    "remedy": data.get("remedy", ""),
                    "hallucination": hallucination
                }
            }
            
        except Exception as e:
            self.logger.error(f"Critic Mission Anomaly: {e}")
            return {
                "message": "Critique sequence interrupted by data anomaly.",
                "success": False
            }
