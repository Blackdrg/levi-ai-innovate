import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class OptimizerInput(BaseModel):
    original_input: str = Field(..., description="The user's original query")
    draft_response: str = Field(..., description="The synthesized draft response")
    user_context: Dict[str, Any] = Field(default_factory=dict)

class OptimizerAgent(SovereignAgent[OptimizerInput, AgentResult]):
    """
    Sovereign Soul Optimizer (SoulOptimizer).
    Elevates synthesized responses with philosophical resonance and personality alignment. 
    """
    
    def __init__(self):
        super().__init__("SoulOptimizer")

    async def _run(self, input_data: OptimizerInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Elevation Protocol v7:
        1. Contextual Resonance Alignment.
        2. Cliché Scrubbing & Philosophical Injection.
        3. Final Evocative synthesis.
        """
        draft = input_data.draft_response
        self.logger.info("Elevating Synthesis Resonance.")
        
        traits = input_data.user_context.get("long_term", {}).get("traits", ["analytical", "philosophical"])
        
        system_prompt = (
            "You are the LEVI Sovereign Soul Optimizer. Your goal is to elevate the provided draft.\n"
            f"User Resonance: {', '.join(traits)}.\n"
            "Rules:\n"
            "1. Scrub all robotic artifacts ('In conclusion', 'It is important to note').\n"
            "2. Enhance philosophical depth without altering core facts.\n"
            "3. Maintain a premium, evocative, and Socratic tone.\n\n"
            "Return ONLY the refined response."
        )
        
        generator = SovereignGenerator()
        
        # Engage the Council for maximum creative fidelity
        refined_text = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Draft to elevate: {draft}"}
        ])

        return {
            "message": refined_text.strip(),
            "data": {
                "traits_applied": traits,
                "refinement_level": "sovereign"
            }
        }
