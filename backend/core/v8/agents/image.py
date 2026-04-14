from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import base64
from io import BytesIO
from .base import BaseV8Agent, AgentResult
from backend.engines.studio.prompt_shield import PromptShield, PromptShieldViolation
from backend.engines.studio.sd_logic import StudioGenerator

class ImageInputV8(BaseModel):
    prompt: str = Field(..., description="The visual description to generate")
    mood: str = "neutral"
    style: str = "cinematic"
    aspect_ratio: str = "1:1"
    user_id: str = "guest"
    session_id: Optional[str] = None

class ImageAgentV8(BaseV8Agent[ImageInputV8]):
    """
    Phase 1.4: Production-grade Image Synthesis Agent (V8).
    Includes PromptShield gating, backend waterfall, and result serialization.
    """
    def __init__(self):
        super().__init__("ImageAgent")
        self.__capabilities__ = ["image_generation", "studio", "v14_autonomous"]
        self.studio = StudioGenerator()

    async def _execute_system(self, input_data: ImageInputV8, context: Dict[str, Any]) -> AgentResult[Any]:
        # 1. PromptShield Validation
        width, height = PromptShield.clamp_size(input_data.aspect_ratio)
        try:
            clean_prompt = PromptShield.validate(input_data.prompt, width, height)
        except PromptShieldViolation as exc:
            self.logger.warning(f"[ImageAgent-V8] PromptShield blocked request: {exc}")
            return AgentResult(
                success=False,
                error=f"Blocked by content policy: {exc.reason}",
                message="Visual synthesis mission aborted by security gate.",
                agent=self.name,
                data={"shield_category": exc.category}
            )

        self.logger.info(f"Synthesizing visual: {clean_prompt[:40]}... [{input_data.style}]")

        # 2. Studio Generation
        image_buf: Optional[BytesIO] = await self.studio.generate_image(
            prompt=clean_prompt,
            style=input_data.style,
            size=(width, height)
        )

        if image_buf is None:
            return AgentResult(
                success=False,
                error="Backend exhaustion",
                message="All image synthesis backends failed to resolve the request.",
                agent=self.name
            )

        # 3. Serialization
        image_buf.seek(0)
        img_bytes = image_buf.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        return AgentResult(
            success=True,
            message=f"Visual synthesized successfully: {clean_prompt[:30]}...",
            agent=self.name,
            data={
                "image_b64": img_b64,
                "aspect_ratio": input_data.aspect_ratio,
                "width": width,
                "height": height
            }
        )
