import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.studio.sd_logic import StudioGenerator

logger = logging.getLogger(__name__)

class ImageInput(BaseModel):
    prompt: str = Field(..., description="The visual description to generate")
    mood: str = "neutral"
    style: str = "cinematic"
    aspect_ratio: str = "1:1"
    user_id: str = "guest"
    image_context: Optional[str] = None  # Base64 or path for local LLaVA analysis

class ImageAgent(SovereignAgent[ImageInput, AgentResult]):
    """
    Sovereign Image Synthesis Agent (VisualArchitect).
    Triggers high-fidelity visual generation missions.
    """
    
    def __init__(self):
        super().__init__("VisualArchitect")

    async def _run(self, input_data: ImageInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Visual Synthesis Protocol v16.1:
        1. Multimodal Perception: If image_context is provided, analyze via LLaVA.
        2. Contextual Enhancement: Refining the vision mission logic.
        3. Synthesis: Executing the vision via Studio Pipeline.
        """
        prompt = input_data.prompt
        vision_analysis = None
        
        # 1. Multimodal Perception (Local LLaVA bridge)
        if input_data.image_context:
            self.logger.info("[VisualArchitect] Image context detected. Engaging LLaVA-1.5...")
            from backend.services.vision_service import vision_service
            vision_analysis = await vision_service.analyze_image(input_data.image_context, prompt)
            self.logger.info(f"[VisualArchitect] Vision Analysis: {vision_analysis[:100]}...")
            # If prompt was just a placeholder, use vision analysis as the new prompt basis
            if len(prompt) < 10 or prompt.lower() in ["analyze", "describe"]:
                 prompt = f"Highly detailed rendering based on: {vision_analysis}"

        self.logger.info(f"Synthesizing Visual Mission: {prompt[:50]}")
        
        # Engage Studio Logic
        studio = StudioGenerator()
        
        # Note: Actual generation happens via the orchestrator bridge
        message = (
            f"Vision manifest: '{prompt[:40]}...'. "
            f"The cinematic synthesis is active using the {input_data.style} engine."
        )
        if vision_analysis:
            message = f"Visual Perception: {vision_analysis}\n\nSynthesis {message}"

        return {
            "message": message,
            "data": {
                "style": input_data.style,
                "mood": input_data.mood,
                "aspect_ratio": input_data.aspect_ratio,
                "vision_analysis": vision_analysis,
                "mission_status": "active"
            }
        }
