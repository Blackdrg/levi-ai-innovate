# pyright: reportMissingImports=false
"""
Stable Diffusion Image Engine for LEVI-AI.

Primary: Local Stable Diffusion via diffusers (requires CUDA GPU).
Fallback: Together AI FLUX API.
"""
import os
import logging
import threading
from io import BytesIO
from typing import Optional, Any

logger = logging.getLogger(__name__)


def _truncate(s: str, n: int) -> str:
    """Pyre2-safe string truncation (avoids slice-overload false-positives)."""
    result = ""
    for i, ch in enumerate(s):
        if i >= n:
            break
        result += ch
    return result

# ─────────────────────────────────────────────
# Style Presets
# ─────────────────────────────────────────────
STYLE_PRESETS = {
    "cinematic": {
        "suffix": "cinematic lighting, film grain, anamorphic lens flare, dramatic shadows, "
                  "35mm film look, depth of field, golden hour, movie still, 8k",
        "negative": "cartoon, anime, drawing, painting, ugly, blurry",
    },
    "anime": {
        "suffix": "anime style, studio ghibli, vibrant colors, detailed illustration, "
                  "cel shading, manga aesthetic, clean lines, high quality anime art",
        "negative": "photorealistic, photograph, 3d render, ugly, blurry",
    },
    "philosophical_art": {
        "suffix": "classical oil painting, chiaroscuro, renaissance style, symbolic, "
                  "allegorical, deep shadows, museum quality, fine art, rembrandt lighting",
        "negative": "cartoon, anime, modern, neon, ugly, blurry",
    },
    "photorealistic": {
        "suffix": "photorealistic, DSLR photography, sharp focus, natural lighting, "
                  "high resolution, professional photograph, 8k uhd, detailed",
        "negative": "cartoon, anime, painting, drawing, illustration, ugly",
    },
    "oil_painting": {
        "suffix": "oil painting on canvas, thick brushstrokes, impasto technique, "
                  "impressionist, rich textures, warm palette, gallery quality, fine art",
        "negative": "photograph, 3d render, cartoon, anime, digital art, ugly",
    },
    "cyberpunk": {
        "suffix": "cyberpunk aesthetic, neon lights, rain-slicked streets, holographic, "
                  "futuristic cityscape, purple and cyan glow, blade runner style, 8k",
        "negative": "natural, daylight, pastoral, rustic, ugly, blurry",
    },
    # ── New styles ──
    "watercolor": {
        "suffix": "watercolor painting, soft washes of color, wet-on-wet technique, "
                  "translucent layers, artistic, dreamlike, paper texture, fine art illustration",
        "negative": "photograph, 3d render, sharp edges, cartoon, dark, ugly, blurry",
    },
    "surrealism": {
        "suffix": "surrealist painting, dreamlike, impossible geometry, melting clocks, "
                  "salvador dali inspired, symbolic, hyper-detailed, strange beauty, 4k",
        "negative": "photograph, realistic, mundane, ugly, blurry, low quality",
    },
    "minimal_line_art": {
        "suffix": "minimalist line art, clean strokes, single continuous line, black and white, "
                  "negative space, elegant simplicity, graphic design, vector aesthetic",
        "negative": "color, photorealistic, painting, messy, cluttered, blurry",
    },
    "default": {
        "suffix": "high quality, detailed, beautiful, artistic, 4k",
        "negative": "ugly, blurry, deformed, low quality",
    },
}


# ─────────────────────────────────────────────
# Prompt Enhancer (uses Groq LLM)
# ─────────────────────────────────────────────
def enhance_prompt(base_prompt: str, style: str = "default") -> str:
    """Use Groq/Llama3 to expand a short prompt into a rich, style-aware image description."""
    style_guidance: dict = {
        "cinematic": "Focus on dramatic lighting, film composition, and color grading.",
        "anime": "Focus on expressive characters, cel-shading, and vibrant anime aesthetics.",
        "philosophical_art": "Focus on symbolic imagery, classical allegory, and chiaroscuro light.",
        "photorealistic": "Focus on real-world details, natural light sources, and camera settings.",
        "oil_painting": "Focus on painterly textures, color mixing, and impressionist atmosphere.",
        "cyberpunk": "Focus on neon glow, rain reflections, holographic overlays, tech decay.",
        "watercolor": "Focus on soft color washes, paper texture, translucency, and gentle edges.",
        "surrealism": "Focus on impossible juxtapositions, dream logic, symbolic objects, and wonder.",
        "minimal_line_art": "Focus on a single elegant flowing line, negative space, and stark simplicity.",
        "default": "Focus on vivid detail, balanced composition, and artistic quality.",
    }
    style_hint = style_guidance.get(style, style_guidance["default"])

    try:
        import groq  # type: ignore
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return base_prompt

        client = groq.Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert image prompt engineer for Stable Diffusion. "
                        "Given a short description and a target art style, expand it into a "
                        "detailed, vivid image generation prompt that perfectly captures the style. "
                        f"Style guidance: {style_hint} "
                        "Include: lighting, composition, atmosphere, textures, colors, mood. "
                        "Output ONLY the enhanced prompt, nothing else. Keep it under 120 words."
                    ),
                },
                {"role": "user", "content": f"Style: {style}. Expand this: {base_prompt}"},
            ],
            max_tokens=180,
            temperature=0.75,
        )
        enhanced = response.choices[0].message.content.strip()
        bp_short = _truncate(str(base_prompt), 40)
        en_short = _truncate(str(enhanced), 80)
        logger.info(f"[PromptEnhancer] '{bp_short}' → '{en_short}…' (style={style})")
        return enhanced
    except Exception as e:
        logger.warning(f"[PromptEnhancer] Failed, using original: {e}")
        return base_prompt


# ─────────────────────────────────────────────
# Stable Diffusion Pipeline (lazy-loaded)
# ─────────────────────────────────────────────
_sd_pipe: Any = None
_sd_lock = threading.Lock()
_sd_available: Optional[bool] = None  # None = not yet checked


# Allow overriding the model via environment variable (e.g. SDXL-Turbo on capable hardware)
_SD_MODEL_ID = os.getenv("SD_MODEL_ID", "runwayml/stable-diffusion-v1-5")


def _load_sd_pipeline() -> Any:
    """Lazy-load the Stable Diffusion pipeline. Returns None if no GPU or missing deps."""
    global _sd_pipe, _sd_available

    if _sd_available is False:
        return None

    with _sd_lock:
        if _sd_pipe is not None:
            return _sd_pipe
        try:
            import torch  # type: ignore
            # Check for CUDA availability
            if not torch.cuda.is_available():
                logger.info("[SD] No CUDA GPU detected. Using Together AI FLUX as primary engine.")
                _sd_available = False
                return None

            # Attempt to load diffusers
            from diffusers import StableDiffusionPipeline  # type: ignore
            logger.info(f"[SD] GPU Detected. Loading model '{_SD_MODEL_ID}'…")
            
            _sd_pipe = StableDiffusionPipeline.from_pretrained(
                _SD_MODEL_ID,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
            ).to("cuda")

            # Enable optimizations
            try:
                _sd_pipe.enable_attention_slicing()
                _sd_pipe.enable_model_cpu_offload() # Save VRAM
                logger.info("[SD] Pipeline optimized for GPU.")
            except Exception:
                pass

            _sd_available = True
            return _sd_pipe
        except Exception as e:
            logger.warning(f"[SD] Local pipeline initialization skipped: {e}. Defaulting to API fallback.")
            _sd_available = False
            return None


# ─────────────────────────────────────────────
# Main Generation Function
# ─────────────────────────────────────────────
def generate(
    prompt: str,
    style: str = "default",
    size: tuple = (1024, 1024),
    enhance: bool = True,
    steps: int = 25,
    guidance_scale: float = 7.5,
) -> Optional[BytesIO]:
    """
    Generate an image using local Stable Diffusion or Together AI fallback.

    Args:
        prompt: The base image description.
        style: One of the STYLE_PRESETS keys.
        size: (width, height) tuple.
        enhance: Whether to use LLM prompt enhancement.
        steps: Number of diffusion steps (SD only).
        guidance_scale: Classifier-free guidance scale (SD only).

    Returns:
        BytesIO containing PNG image data, or None on failure.
    """
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["default"])

    # Enhance the prompt with LLM
    if enhance:
        prompt = enhance_prompt(prompt, style)

    # Append style suffix
    full_prompt = f"{prompt}, {style_config['suffix']}"
    negative_prompt = style_config["negative"]

    # ── Try Local Stable Diffusion ──
    pipe = _load_sd_pipeline()
    if pipe is not None:
        try:
            import torch  # type: ignore
            logger.info(f"[SD] Generating: '{full_prompt[:80]}…' (style={style})")

            # SD v1.5 native resolution is 512x512; scale up after
            with torch.no_grad():
                result = pipe(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=steps,
                    guidance_scale=guidance_scale,
                    width=512,
                    height=512,
                )
            image = result.images[0]

            # Upscale to requested size if different
            if size != (512, 512):
                from PIL import Image  # type: ignore
                image = image.resize(size, Image.Resampling.LANCZOS)

            buf = BytesIO()
            image.save(buf, format="PNG", optimize=True)
            buf.seek(0)
            logger.info("[SD] Image generated successfully (local).")
            return buf

        except Exception as e:
            logger.error(f"[SD] Local generation failed: {e}")
            # Fall through to Together AI

    # ── Fallback: Together AI FLUX ──
    return _generate_via_together(full_prompt, size)


def _generate_via_together(prompt: str, size: tuple) -> Optional[BytesIO]:
    """Fallback image generation via Together AI FLUX API."""
    import requests  # type: ignore

    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        logger.warning("[Together] No API key. Cannot generate image.")
        return None

    try:
        import base64
        from PIL import Image  # type: ignore

        resp = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": f"{prompt}, no text, no words, wallpaper quality",
                "width": size[0],
                "height": size[1],
                "steps": 4,
                "n": 1,
                "response_format": "b64_json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        img_b64 = data["data"][0]["b64_json"]
        img_bytes = base64.b64decode(img_b64)
        img = Image.open(BytesIO(img_bytes)).convert("RGB")

        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        logger.info("[Together] Image generated successfully (fallback).")
        return buf

    except Exception as e:
        logger.error(f"[Together] Image generation failed: {e}")
        return None


# ─────────────────────────────────────────────
# Utility: List available styles
# ─────────────────────────────────────────────
def get_available_styles() -> list:
    """Return list of available style names."""
    return [k for k in STYLE_PRESETS.keys() if k != "default"]


# ─────────────────────────────────────────────
# Public alias — clean import name for API layer
# ─────────────────────────────────────────────
def generate_image(
    prompt: str,
    style: str = "default",
    size: tuple = (1024, 1024),
    enhance: bool = True,
    steps: int = 25,
    guidance_scale: float = 7.5,
) -> Optional[BytesIO]:
    """
    Public alias for `generate()`. Preferred entry point for external callers.

    Returns BytesIO containing PNG image data, or None on failure.
    """
    return generate(prompt, style=style, size=size, enhance=enhance,
                    steps=steps, guidance_scale=guidance_scale)
