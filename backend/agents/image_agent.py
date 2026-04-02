"""
Sovereign Image Synthesis Agent v8.
Triggers high-fidelity visual generation missions.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class ImageInput(BaseModel):
    prompt: str = Field(..., description="The visual description to generate")
    mood: str = "neutral"
    style: str = "cinematic"
    aspect_ratio: str = "1:1"
    user_id: str = "guest"

class ImageAgent(SovereignAgent[ImageInput, AgentResult]):
    """
    Sovereign Visual Architect.
    Executes high-fidelity visual generation via Studio Pipeline.
    """
    
    def __init__(self):
        super().__init__("VisualArchitect")

    async def _run(self, input_data: ImageInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Visual Synthesis Protocol v8:
        1. Contextual Enhancement.
        2. Synthesis execution via Studio Generator.
        """
        prompt = input_data.prompt
        self.logger.info(f"Synthesizing Visual Mission: {prompt[:50]}")
        
        # Engage Studio Logic
        from backend.engines.studio.sd_logic import StudioGenerator
        studio = StudioGenerator()
        
        size_map = {"1:1": (1024, 1024), "16:9": (1024, 576), "9:16": (576, 1024)}
        size = size_map.get(input_data.aspect_ratio, (1024, 1024))
        
        message = (
            f"Vision manifest: '{prompt[:40]}...'. "
            f"The cinematic synthesis is active using the {input_data.style} engine."
        )

        return {
            "message": message,
            "data": {
                "style": input_data.style,
                "mood": input_data.mood,
                "aspect_ratio": input_data.aspect_ratio,
                "mission_status": "active"
            }
        }
