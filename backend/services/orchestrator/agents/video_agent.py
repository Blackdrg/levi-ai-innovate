"""
backend/services/orchestrator/agents/video_agent.py
"""

import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.services.studio.utils import create_studio_job

logger = logging.getLogger(__name__)

class VideoInput(BaseModel):
    prompt: str = Field(..., description="The script or visual description for the video")
    mood: str = "neutral"
    style: str = "cinematic"
    aspect_ratio: str = "9:16"
    motion_bucket_id: int = 127
    user_id: str = "guest"
    user_tier: str = "free"

class VideoAgent(BaseTool[VideoInput, StandardToolOutput]):
    name = "video_agent"
    description = "Video synthesis engine. Triggers multi-scene video generation jobs."
    input_schema = VideoInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: VideoInput, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[VideoAgent] Initiating video job for: {input_data.prompt[:50]}...")
        
        # Trigger the real studio job
        job_result = create_studio_job(
            task_type="video",
            params={
                "text": input_data.prompt,
                "mood": input_data.mood,
                "style": input_data.style,
                "aspect_ratio": input_data.aspect_ratio,
                "motion_bucket_id": input_data.motion_bucket_id,
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
            
        job_id = job_result.get("job_id")
        
        return {
            "success": True,
            "message": f"I have initiated your {input_data.style} video synthesis. [Job ID: {job_id}]. The cinematic flow is now in motion.",
            "data": {"job_id": job_id, "type": "video", "aspect_ratio": input_data.aspect_ratio},
            "agent": self.name
        }
