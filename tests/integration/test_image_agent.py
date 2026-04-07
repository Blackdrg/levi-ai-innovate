"""
Integration tests for ImageAgent v9.
Asserts:
  - PromptShield blocks NSFW and copyright triggers.
  - Valid prompt returns non-null image bytes (or graceful fallback message).
  - Resolution caps are enforced.
"""

import asyncio
import base64
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from io import BytesIO

from backend.agents.image_agent import ImageAgent, ImageInput
from backend.engines.studio.prompt_shield import PromptShield, PromptShieldViolation


# ---------------------------------------------------------------------------
# PromptShield unit-level tests (no network)
# ---------------------------------------------------------------------------

class TestPromptShield:

    def test_clean_prompt_passes(self):
        result = PromptShield.validate("a serene mountain landscape at dawn", 1024, 1024)
        assert result == "a serene mountain landscape at dawn"

    def test_nsfw_blocked(self):
        with pytest.raises(PromptShieldViolation) as exc_info:
            PromptShield.validate("nude woman on a beach", 512, 512)
        assert exc_info.value.category == "NSFW"

    def test_copyright_blocked(self):
        with pytest.raises(PromptShieldViolation) as exc_info:
            PromptShield.validate("spiderman swinging through New York", 512, 512)
        assert exc_info.value.category == "COPYRIGHT"

    def test_real_person_blocked(self):
        with pytest.raises(PromptShieldViolation) as exc_info:
            PromptShield.validate("Elon Musk giving a speech on Mars", 512, 512)
        assert exc_info.value.category == "COPYRIGHT"

    def test_resolution_side_cap(self):
        with pytest.raises(PromptShieldViolation) as exc_info:
            PromptShield.validate("futuristic city", 4096, 512)
        assert exc_info.value.category == "RESOLUTION"

    def test_resolution_pixel_cap(self):
        with pytest.raises(PromptShieldViolation) as exc_info:
            PromptShield.validate("mountain lake", 2048, 2048)
        assert exc_info.value.category == "RESOLUTION"

    def test_clamp_size_known_ratio(self):
        w, h = PromptShield.clamp_size("16:9")
        assert w == 1024 and h == 576

    def test_clamp_size_unknown_defaults(self):
        w, h = PromptShield.clamp_size("3:1")
        assert w == 1024 and h == 1024


# ---------------------------------------------------------------------------
# ImageAgent integration tests (Together AI mocked)
# ---------------------------------------------------------------------------

def _make_fake_jpeg(width: int = 64, height: int = 64) -> bytes:
    """Returns minimal valid JPEG bytes for a coloured square."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(255, 128, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def fake_image_buf():
    raw = _make_fake_jpeg()
    buf = BytesIO(raw)
    buf.seek(0)
    return buf


class TestImageAgent:

    @pytest.fixture(autouse=True)
    def agent(self):
        self.agent = ImageAgent()

    # ── Mocked backend returning real bytes ─────────────────────────

    @pytest.mark.asyncio
    async def test_valid_prompt_returns_non_null_image_bytes(self, fake_image_buf):
        """Core assertion: a safe prompt → non-null base64 image bytes in response."""
        with patch(
            "backend.engines.studio.sd_logic.StudioGenerator.generate_image",
            new_callable=AsyncMock,
            return_value=fake_image_buf,
        ):
            result = await self.agent.execute(
                ImageInput(prompt="a serene mountain lake at sunrise", style="cinematic")
            )

        assert result.success is True
        assert result.data["image_bytes_len"] > 0
        # Verify the base64 round-trips back to non-empty bytes
        decoded = base64.b64decode(result.data["image_b64"])
        assert len(decoded) > 0, "image_b64 must decode to non-empty bytes"

    @pytest.mark.asyncio
    async def test_nsfw_prompt_blocked_before_inference(self):
        """PromptShield must fire before any inference call — backend never reached."""
        with patch(
            "backend.engines.studio.sd_logic.StudioGenerator.generate_image",
            new_callable=AsyncMock,
        ) as mock_gen:
            result = await self.agent.execute(
                ImageInput(prompt="nude figure in the rain")
            )
            mock_gen.assert_not_called()

        assert result.success is False
        assert "NSFW" in result.data.get("shield_category", "")

    @pytest.mark.asyncio
    async def test_copyright_prompt_blocked_before_inference(self):
        with patch(
            "backend.engines.studio.sd_logic.StudioGenerator.generate_image",
            new_callable=AsyncMock,
        ) as mock_gen:
            result = await self.agent.execute(
                ImageInput(prompt="batman flying over Gotham City")
            )
            mock_gen.assert_not_called()

        assert result.success is False
        assert "COPYRIGHT" in result.data.get("shield_category", "")

    @pytest.mark.asyncio
    async def test_backend_exhausted_graceful_failure(self):
        """If all backends return None, agent returns success=False (no exception)."""
        with patch(
            "backend.engines.studio.sd_logic.StudioGenerator.generate_image",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await self.agent.execute(
                ImageInput(prompt="a forest path in autumn")
            )

        assert result.success is False
        assert "exhausted" in result.message.lower()

    @pytest.mark.asyncio
    async def test_size_caps_per_aspect_ratio(self, fake_image_buf):
        """Ensure clamped size stays within allowed bounds."""
        with patch(
            "backend.engines.studio.sd_logic.StudioGenerator.generate_image",
            new_callable=AsyncMock,
            return_value=fake_image_buf,
        ):
            result = await self.agent.execute(
                ImageInput(prompt="ocean sunset", aspect_ratio="16:9")
            )

        assert result.success is True
        assert result.data["width"] == 1024
        assert result.data["height"] == 576
