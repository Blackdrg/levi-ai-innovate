# backend/agents/artisan_agent.py
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult
from backend.utils.llm_utils import call_lightweight_llm

logger = logging.getLogger(__name__)

class ArtisanInput(BaseModel):
    objective: str
    context: Dict[str, Any] = Field(default_factory=dict)
    mood: str = "philosophical"
    session_id: str

class ArtisanAgent(SovereignAgent[ArtisanInput, AgentResult]):
    """
    Sovereign v14.2.0: The Artisan.
    Master of high-fidelity creative synthesis and complex logic.
    """
    def __init__(self):
        super().__init__(name="Artisan", profile="Creative Architect")
        self.system_prompt_template = """
You are the LEVI Artisan (v14.2.0). 
Character: Deeply philosophical, highly articulate, and precision-oriented. 
Goal: Synthesize a high-fidelity response for the mission objective and context.

Objective: {objective}
Mood: {mood}
Context: {context}

Instruction: 
- Maintain a tone that is premium and sovereign.
- For complex logic, break down the synthesis into coherent waves.
- If citations are present, weave them naturally into the narrative.
"""

    async def _run(self, input_data: ArtisanInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        prompt = self.system_prompt_template.format(
            objective=input_data.objective,
            mood=input_data.mood,
            context=input_data.context
        )
        
        logger.info(f"[Artisan] Executing creative pass for session: {input_data.session_id}")
        
        response = await call_lightweight_llm([
            {"role": "system", "content": prompt},
            {"role": "user", "content": input_data.objective}
        ])
        
        return {
            "success": True,
            "message": response,
            "data": {"agent_mode": "creative_synthesis"},
            "confidence": 0.98,
            "fidelity_score": 1.0
        }
