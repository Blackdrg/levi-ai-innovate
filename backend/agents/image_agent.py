"""
Sovereign Image Synthesis Agent v9.
Wired to real inference backends (ComfyUI / SD-WebUI local, Together AI cloud).
PromptShield contract enforced at agent boundary before every inference call.
"""

import logging
import base64
from io import BytesIO
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.studio.prompt_shield import PromptShield, PromptShieldViolation

logger = logging.getLogger(__name__)


class ImageInput(BaseModel):
    prompt: str = Field(..., description="The visual description to generate")
    mood: str = "neutral"
    style: str = "cinematic"
    aspect_ratio: str = "1:1"
    user_id: str = "guest"
    session_id: Optional[str] = None


class ImageAgent(SovereignAgent[ImageInput, AgentResult]):
    """
    Sovereign Visual Architect v9.
    Backend priority: ComfyUI (local SDXL) → SD-WebUI (local) → Together AI (cloud).
    PromptShield gates every request before any network call is made.
    """

    def __init__(self):
        super().__init__("VisualArchitect")

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _run(self, input_data: ImageInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Visual Synthesis Protocol v9:
        1. PromptShield validation (raises on NSFW / copyright / size breach).
        2. Size canonicalisation.
        3. Backend waterfall: ComfyUI → SD-WebUI → Together AI.
        4. Return non-null image bytes as base64 + metadata.
        """
        # ── 1. PromptShield ────────────────────────────────────────────
        width, height = PromptShield.clamp_size(input_data.aspect_ratio)
        try:
            clean_prompt = PromptShield.validate(input_data.prompt, width, height)
        except PromptShieldViolation as exc:
            self.logger.warning("[VisualArchitect] PromptShield blocked request: %s", exc)
            return {
                "success": False,
                "message": f"Request blocked by content policy: {exc.reason}",
                "data": {"shield_category": exc.category},
            }

        self.logger.info("Synthesising visual: %s… [%s @ %dx%d]", clean_prompt[:40], input_data.style, width, height)

        # ── 2. Studio engine ───────────────────────────────────────────
        from backend.engines.studio.sd_logic import StudioGenerator
        studio = StudioGenerator()

        image_buf: Optional[BytesIO] = await studio.generate_image(
            prompt=clean_prompt,
            style=input_data.style,
            size=(width, height),
        )

        if image_buf is None:
            return {
                "success": False,
                "message": "All image backends exhausted — no image could be generated.",
                "data": {"aspect_ratio": input_data.aspect_ratio},
            }

        # ── 3. Encode to base64 for serialisation ─────────────────────
        image_buf.seek(0)
        img_bytes = image_buf.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        return {
            "success": True,
            "message": f"Visual synthesised: '{clean_prompt[:40]}…' [{input_data.style}]",
            "data": {
                "image_b64": img_b64,
                "image_bytes_len": len(img_bytes),
                "style": input_data.style,
                "mood": input_data.mood,
                "aspect_ratio": input_data.aspect_ratio,
                "width": width,
                "height": height,
                "mission_status": "completed",
            },
        }
