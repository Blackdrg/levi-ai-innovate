"""
backend/services/orchestrator/agents/image_agent.py
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.services.studio.utils import create_studio_job

logger = logging.getLogger(__name__)

class ImageInput(BaseModel):
    prompt: str = Field(..., description="The visual description to generate")
    mood: str = "neutral"
    style: str = "cinematic"
    aspect_ratio: str = "1:1"
    negative_prompt: str = "low quality, text, blurry, distorted"
    seed: Optional[int] = None
    user_id: str = "guest"
    user_tier: str = "free"

class ImageAgent(BaseTool[ImageInput, StandardToolOutput]):
    name = "image_agent"
    description = "Visual synthesis engine. Triggers high-fidelity image generation jobs."
    input_schema = ImageInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: ImageInput, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ImageAgent] Initiating job for: {input_data.prompt[:50]}...")
        
        # Trigger the real studio job
        job_result = create_studio_job(
            task_type="image",
            params={
                "text": input_data.prompt,
                "mood": input_data.mood,
                "style": input_data.style,
                "aspect_ratio": input_data.aspect_ratio,
                "negative_prompt": input_data.negative_prompt,
                "seed": input_data.seed,
                "author": "LEVI-AI"
            },
            user_id=input_data.user_id,
            user_tier=input_data.user_tier
        )
        
        if job_result.get("status") == "error":
            return {
                "success": False,
                "error": job_result.get("error"),
                "agent": self.name
            }

        return {
            "success": True,
            "message": f"I have visualized your concept: '{input_data.prompt[:40]}...'. The masterpiece is being rendered via the {input_data.style} engine.",
            "data": {"job_id": job_result.get("job_id"), "aspect_ratio": input_data.aspect_ratio},
            "agent": self.name
        }
