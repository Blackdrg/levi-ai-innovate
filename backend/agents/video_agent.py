"""
Sovereign Video Synthesis Agent v9.
Wired to: local AnimateDiff (via Ollama-compatible wrapper) with 30-frame cap,
and a cloud fallback via Replicate API behind CloudFallbackProxy.
FrameConsistency validator enforced on all outputs.
"""

import os
import logging
import asyncio
import json
import base64
from io import BytesIO
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.video.frame_consistency import (
    FrameConsistencyValidator,
    FrameConsistencyError,
    MAX_FRAMES,
)

logger = logging.getLogger(__name__)

# Cloud fallback endpoints
REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"
ANIMATEDIFF_LOCAL_URL = os.getenv("ANIMATEDIFF_URL", "http://localhost:7860/animatediff")


class VideoInput(BaseModel):
    prompt: str = Field(..., description="The script or visual description for the video")
    mood: str = "neutral"
    style: str = "cinematic"
    aspect_ratio: str = "9:16"
    num_frames: int = Field(default=16, ge=4, le=MAX_FRAMES, description=f"Frame count (max {MAX_FRAMES})")
    fps: int = Field(default=8, ge=4, le=24)
    user_id: str = "guest"
    session_id: Optional[str] = None


class VideoAgent(SovereignAgent[VideoInput, AgentResult]):
    """
    Sovereign Motion Architect v9.
    Backend waterfall: AnimateDiff local → Replicate cloud.
    FrameConsistency validator rejects outputs with >15% inter-frame delta.
    Frame count hard-capped at MAX_FRAMES (30).
    """

    def __init__(self):
        super().__init__("MotionArchitect")
        self._validator = FrameConsistencyValidator()
        self._replicate_key = os.getenv("REPLICATE_API_TOKEN", "")

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _run(self, input_data: VideoInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Cinematic Synthesis Protocol v9:
        1. Clamp frame count.
        2. Try local AnimateDiff.
        3. Fallback to Replicate cloud.
        4. Run FrameConsistency validator.
        5. Return frames as base64-encoded list.
        """
        num_frames = min(input_data.num_frames, MAX_FRAMES)
        prompt = input_data.prompt.strip()

        self.logger.info("Motion mission: '%s…' (%d frames @ %d fps)", prompt[:50], num_frames, input_data.fps)

        frames: Optional[List[bytes]] = None

        # ── 1. Local AnimateDiff attempt ───────────────────────────────
        frames = await self._try_local_animatediff(prompt, num_frames, input_data)

        # ── 2. Cloud fallback (Replicate / AnimateDiff-v3) ─────────────
        if frames is None:
            self.logger.info("[MotionArchitect] Local backend unavailable — escalating to Replicate.")
            frames = await self._try_replicate(prompt, num_frames, input_data)

        if frames is None:
            return {
                "success": False,
                "message": "All video backends exhausted — no frames generated.",
                "data": {"prompt_preview": prompt[:60]},
            }

        # ── 3. FrameConsistency validation ─────────────────────────────
        try:
            variance = self._validator.validate(frames)
        except FrameConsistencyError as exc:
            self.logger.warning("[MotionArchitect] Frame consistency rejected: %s", exc)
            return {
                "success": False,
                "message": f"Video rejected: inter-frame variance {exc.variance:.2%} > threshold {exc.threshold:.2%}.",
                "data": {"variance": exc.variance, "threshold": exc.threshold},
            }

        # ── 4. Encode frames ───────────────────────────────────────────
        encoded_frames = [base64.b64encode(f).decode("utf-8") for f in frames]

        return {
            "success": True,
            "message": f"Motion synthesised: '{prompt[:40]}…' — {len(frames)} frames.",
            "data": {
                "frames_b64": encoded_frames,
                "frame_count": len(frames),
                "fps": input_data.fps,
                "aspect_ratio": input_data.aspect_ratio,
                "frame_delta_variance": round(variance, 4),
                "style": input_data.style,
                "mood": input_data.mood,
                "job_status": "completed",
            },
        }

    # ------------------------------------------------------------------
    # Backend: Local AnimateDiff
    # ------------------------------------------------------------------

    async def _try_local_animatediff(
        self, prompt: str, num_frames: int, inp: VideoInput
    ) -> Optional[List[bytes]]:
        """
        POST to local AnimateDiff / Automatic1111 with AnimateDiff extension.
        Returns list of raw JPEG/PNG frame bytes, or None on failure.
        """
        try:
            payload = {
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, watermark",
                "num_frames": num_frames,
                "fps": inp.fps,
                "guidance_scale": 7.5,
                "num_inference_steps": 20,
            }
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(ANIMATEDIFF_LOCAL_URL, json=payload) as resp:
                    if resp.status != 200:
                        logger.debug("[AnimateDiff] Non-200 response: %d", resp.status)
                        return None
                    data = await resp.json()
                    raw_frames = data.get("frames", [])
                    if not raw_frames:
                        return None
                    # Frames may be base64-encoded strings
                    result: List[bytes] = []
                    for f in raw_frames:
                        if isinstance(f, str):
                            result.append(base64.b64decode(f))
                        elif isinstance(f, (bytes, bytearray)):
                            result.append(bytes(f))
                    return result if result else None
        except Exception as exc:
            logger.debug("[AnimateDiff] Local attempt failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Backend: Replicate cloud (AnimateDiff v3)
    # ------------------------------------------------------------------

    async def _try_replicate(
        self, prompt: str, num_frames: int, inp: VideoInput
    ) -> Optional[List[bytes]]:
        """
        Submits a prediction to Replicate using the lucataco/animate-diff-v3 model,
        polls until completion, downloads the output frames.
        """
        if not self._replicate_key:
            logger.warning("[MotionArchitect] REPLICATE_API_TOKEN not set — cloud fallback skipped.")
            return None

        headers = {
            "Authorization": f"Token {self._replicate_key}",
            "Content-Type": "application/json",
        }
        # lucataco/animate-diff-v3 on Replicate
        create_payload = {
            "version": "df6f9d326b84e2cec687e8a458cb4d55ee7f6b3b5b5c4a5c2d3e1f0c6b4e8d2",  # pinned version
            "input": {
                "prompt": prompt,
                "negative_prompt": "blurry, ugly, watermark",
                "num_frames": num_frames,
                "fps": inp.fps,
                "guidance_scale": 7.5,
            },
        }

        try:
            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                # 1. Create prediction
                async with session.post(REPLICATE_API_URL, json=create_payload) as r:
                    if r.status not in (200, 201):
                        logger.warning("[Replicate] Create failed: %d", r.status)
                        return None
                    prediction = await r.json()

                pred_id = prediction.get("id")
                if not pred_id:
                    return None

                # 2. Poll for completion (max 120 s)
                poll_url = f"{REPLICATE_API_URL}/{pred_id}"
                for _ in range(60):
                    await asyncio.sleep(2)
                    async with session.get(poll_url) as r:
                        state = await r.json()
                    status = state.get("status")
                    if status == "succeeded":
                        output_urls: List[str] = state.get("output", [])
                        break
                    if status in ("failed", "canceled"):
                        logger.warning("[Replicate] Prediction %s %s", pred_id, status)
                        return None
                else:
                    logger.warning("[Replicate] Prediction %s timed out.", pred_id)
                    return None

                # 3. Download frames
                frames: List[bytes] = []
                for url in output_urls[:num_frames]:
                    async with session.get(url) as r:
                        frames.append(await r.read())
                return frames if frames else None

        except Exception as exc:
            logger.error("[Replicate] Cloud fallback error: %s", exc)
            return None
