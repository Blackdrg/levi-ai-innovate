"""
backend/services/orchestrator/agents/image_agent.py
"""

import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.services.studio.utils import create_studio_job

logger = logging.getLogger(__name__)

class ImageInput(BaseModel):
    prompt: str = Field(..., description="The visual description to generate")
    mood: str = "neutral"
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
            "message": f"I have visualized your concept: '{input_data.input}'. The masterpiece is being rendered.",
            "data": {"job_id": result.get("job_id")},
            "agent": self.name
        }
