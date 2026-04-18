# backend/agents/vision.py
import logging
from typing import Dict, Any, List, Optional
from backend.agents.base import BaseAgent, AgentInput, AgentOutput

logger = logging.getLogger(__name__)

class VisionAgent(BaseAgent):
    """
    Sovereign Vision: The Multimodal Sensor.
    Processes images, videos, and complex spatial data for visual reasoning.
    """

    def __init__(self):
        super().__init__(
            agent_id="vision_agent",
            name="Vision",
            role="Multimodal Perception",
            goal="Analyze and synthesize visual data with high-fidelity reasoning."
        )

    async def _run(self, input_data: AgentInput) -> AgentOutput:
        """Processes visual media input."""
        objective = input_data.objective
        media_paths = input_data.context.get("media_paths", [])
        
        logger.info(f"👁️ [Vision] analyzing {len(media_paths)} assets for objective: {objective}")
        
        # 1. Engage Multimodal Model
        from backend.utils.llm_utils import call_vision_model
        
        try:
            analysis = await call_vision_model(
                prompt=objective,
                image_paths=media_paths
            )
            
            return AgentOutput(
                agent_id=self.agent_id,
                success=True,
                output=analysis,
                data={"asset_count": len(media_paths), "provider": "Sovereign-Vision-v1"}
            )
        except Exception as e:
            logger.error(f"[Vision] Capture anomaly: {e}")
            return AgentOutput(
                agent_id=self.agent_id,
                success=False,
                output=f"Vision capture failed: {e}",
                data={}
            )
