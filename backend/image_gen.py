# pyright: reportMissingImports=false
"""
LEVI Image Generation Engine v3.0
- Together AI FLUX (primary)
- Local Stable Diffusion (GPU optional)
- Advanced PIL compositing with 12+ style presets
- S3 upload + CDN support
- Prompt enhancement via Groq
"""

import os
import base64
import random
import textwrap
import logging
import uuid
from backend.firestore_db import db as firestore_db  # type: ignore
from backend.redis_client import cache_search, get_cached_search, HAS_REDIS  # type: ignore
from backend.embeddings import embed_text  # type: ignore
from backend.sd_engine import sd_gen_image  # type: ignore
from io import BytesIO
from typing import Optional, Any, Tuple
import requests  # type: ignore

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance  # type: ignore
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type  # type: ignore

logger = logging.getLogger(__name__)

from backend.s3_utils import upload_image_to_s3 # type: ignore

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_API_URL = "https://api.together.xyz/v1/images/generations"
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

Image.MAX_IMAGE_PIXELS = 50_000_000

# ─────────────────────────────────────────────
# MOOD → VISUAL PROMPT MAPPING
# ─────────────────────────────────────────────

MOOD_PROMPTS = {
    "inspiring": "golden sunrise bursting through mountain peaks, god rays, epic cloudscape, cinematic composition, 8k",
    "calm": "still mountain lake at dawn, soft mist, reflections, zen garden stones, watercolor atmosphere",
    "energetic": "electric storm over neon cityscape, lightning streaks, dynamic motion blur, vibrant plasma colors",
    "philosophical": "ancient cosmic library floating in nebula, bookshelves extending to infinity, deep space, ethereal blue",
    "melancholic": "solitary figure on rain-soaked cobblestones, gaslit streets, soft bokeh, cinematic blue hour",
    "stoic": "ancient marble columns at sunrise, weathered stone, classical Roman architecture, muted gold tones",
    "zen": "bamboo forest at golden hour, shafts of light, Japanese aesthetic, morning dew, tranquil path",
    "cyberpunk": "neon-soaked cyberpunk cityscape, holographic billboards, rain reflections, purple cyan glow, Blade Runner",
    "futuristic": "sleek orbital station above Earth, clean white surfaces, blue bioluminescent accents, zero gravity",
    "neutral": "abstract flowing aurora gradients, soft cosmic colors, dreamy depth of field, artistic blur",
    "mystical": "ancient temple ruins overgrown with glowing plants, bioluminescent forest, sacred geometry, moonlight",
    "dark": "dramatic chiaroscuro lighting, obsidian surfaces, single candle flame, shadow architecture, baroque style",
}

# Style presets for SD/Together
STYLE_ENHANCERS = {
    "cinematic": ", cinematic film grain, anamorphic bokeh, dramatic shadows, golden hour, movie still, 8k uhd",
    "oil_painting": ", oil painting texture, thick impasto brushstrokes, renaissance masters, rich saturated palette",
    "watercolor": ", loose watercolor washes, wet-on-wet blooms, paper texture, translucent layers, artist sketch",
    "digital_art": ", digital illustration, clean lines, vibrant gradient fills, concept art, artstation trending",
    "photorealistic": ", DSLR photograph, sharp focus, natural lighting, 85mm lens, photorealistic, award winning",
    "abstract": ", abstract expressionism, color field painting, dynamic composition, Jackson Pollock energy",
    "minimal": ", minimalist composition, negative space, single focal point, clean aesthetic, zen simplicity",
}


def _enhance_prompt_with_groq(base_prompt: str, mood: str, style: str = "") -> str:
    """Use Groq to expand a short prompt into a rich image description."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return base_prompt

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert image prompt engineer. Expand the given description "
                            f"into a rich, detailed image generation prompt with {mood} mood and {style or 'artistic'} style. "
                            "Include: lighting, atmosphere, composition, colors, mood, textures. "
                            "Output ONLY the enhanced prompt, no explanations. Keep it under 100 words. "
                            "End with: no text, no words, no letters, masterpiece quality."
                        )
                    },
                    {"role": "user", "content": f"Expand this for image generation: {base_prompt}"}
                ],
                "max_tokens": 150,
                "temperature": 0.7,
            },
            timeout=6
        )
        if resp.status_code == 200:
            enhanced = resp.json()["choices"][0]["message"]["content"].strip()
            return enhanced
    except Exception as e:
        logger.warning(f"Prompt enhancement failed: {e}")
    return base_prompt


def build_prompt(quote: str, mood: str, style: str = "", enhance: bool = True) -> str:
    """Build a rich image prompt from quote + mood."""
    base = MOOD_PROMPTS.get(mood.lower(), MOOD_PROMPTS["neutral"])

    # Extract key words from quote
    stop_words = {"the", "a", "an", "is", "are", "to", "of", "and", "or", "in",
                  "it", "you", "we", "i", "me", "that", "this", "was", "be"}
    words = [w.strip(".,!?\"'—") for w in quote.lower().split() if len(w) > 3]
    key_words = [w for w in words if w not in stop_words][:3]
    keywords = " ".join(key_words)

    base_prompt = f"{base}, {keywords}" if keywords else base
    style_suffix = STYLE_ENHANCERS.get(style, "")
    full_prompt = f"{base_prompt}{style_suffix}, no text, no words, wallpaper quality, ultra detailed"

    if enhance:
        full_prompt = _enhance_prompt_with_groq(full_prompt, mood, style)

    return full_prompt


# ─────────────────────────────────────────────
# TOGETHER AI — Primary Image Generation
# ─────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((requests.exceptions.RequestException, Exception)),
    reraise=True
)
def generate_via_together(prompt: str, size: Tuple[int, int] = (1024, 1024),
                          model: str = "black-forest-labs/FLUX.1-schnell") -> Image.Image:
    """Call Together AI to generate a background image."""
    if not TOGETHER_API_KEY:
        raise ValueError("TOGETHER_API_KEY not set")

    payload = {
        "model": model,
        "prompt": prompt,
        "width": size[0],
        "height": size[1],
        "steps": 4,
        "n": 1,
        "response_format": "b64_json"
    }

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(TOGETHER_API_URL, json=payload, headers=headers, timeout=90)

    if resp.status_code == 429:
        retry_after = float(resp.headers.get("Retry-After", 5))
        import time
        time.sleep(retry_after)
        raise requests.exceptions.RequestException("Rate limited")

    resp.raise_for_status()
    data = resp.json()

    img_b64 = data["data"][0]["b64_json"]
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")

    if img.size != size:
        from PIL import ImageOps  # type: ignore
        img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)

    return img


# ─────────────────────────────────────────────
# PIL FALLBACK — Gradient + Noise Generation
# ─────────────────────────────────────────────

def generate_gradient_fallback(mood: str, size: Tuple[int, int]) -> Image.Image:
    """Generate a visually rich gradient as fallback."""
    mood_palettes = {
        "inspiring":     [(40, 0, 80), (120, 60, 20), (200, 150, 0)],
        "calm":          [(10, 40, 60), (20, 80, 120), (100, 180, 180)],
        "energetic":     [(80, 0, 20), (200, 60, 0), (255, 140, 0)],
        "philosophical": [(5, 5, 25), (20, 20, 70), (60, 40, 120)],
        "melancholic":   [(5, 10, 30), (20, 30, 80), (60, 80, 140)],
        "stoic":         [(30, 25, 20), (80, 70, 60), (140, 130, 110)],
        "zen":           [(15, 30, 15), (40, 80, 40), (100, 150, 80)],
        "cyberpunk":     [(15, 0, 30), (80, 0, 160), (200, 0, 255)],
        "futuristic":    [(0, 5, 25), (0, 60, 140), (0, 180, 255)],
        "neutral":       [(15, 20, 40), (50, 60, 100), (100, 110, 160)],
        "mystical":      [(20, 0, 40), (60, 20, 100), (120, 40, 180)],
        "dark":          [(5, 5, 5), (30, 25, 20), (70, 60, 50)],
    }

    colors = mood_palettes.get(mood.lower(), mood_palettes["neutral"])

    img = Image.new("RGBA", size, (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Multi-stop gradient
    h = size[1]
    w = size[0]
    for y in range(h):
        progress = y / h
        if progress < 0.5:
            t = progress * 2
            c1, c2 = colors[0], colors[1]
        else:
            t = (progress - 0.5) * 2
            c1, c2 = colors[1], colors[2] if len(colors) > 2 else colors[1]
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # Add subtle noise texture
    try:
        import numpy as np  # type: ignore
        noise = np.random.randint(0, 15, (size[1], size[0], 3), dtype=np.uint8)
        noise_img = Image.fromarray(noise, 'RGB').convert('RGBA')
        noise_img.putalpha(30)  # Very subtle
        img = Image.alpha_composite(img, noise_img)
    except ImportError:
        pass

    return img


# ─────────────────────────────────────────────
# COMPOSITING — Text Overlay + Effects
# ─────────────────────────────────────────────

def add_dark_overlay(img: Image.Image, mood: str, opacity: int = 140) -> Image.Image:
    """Add a dark overlay to ensure text readability."""
    mood_opacities = {
        "philosophical": 165, "melancholic": 170, "cyberpunk": 155, "dark": 180,
        "stoic": 145, "neutral": 130, "inspiring": 120, "zen": 125,
    }
    actual_opacity = mood_opacities.get(mood.lower(), opacity)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, actual_opacity))
    return Image.alpha_composite(img, overlay)


def add_vignette(img: Image.Image, strength: int = 120) -> Image.Image:
    """Apply a radial vignette effect."""
    w, h = img.size
    vignette = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)

    steps = 80
    for i in range(steps):
        alpha = int(strength * (1 - (i / steps) ** 0.6))
        margin = int((i / steps) * min(w, h) * 0.6)
        if margin < min(w // 2, h // 2):
            draw.rectangle([margin, margin, w - margin, h - margin],
                           outline=(0, 0, 0, alpha), width=3)

    return Image.alpha_composite(img, vignette)


def load_font(size: int, mood: str = "", bold: bool = False) -> Any:
    """Load the best available font for the mood."""
    serif_moods = {"philosophical", "stoic", "zen", "melancholic", "calm", "mystical", "dark"}
    prefer_serif = mood.lower() in serif_moods

    font_candidates = []
    if prefer_serif:
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
            "Georgia", "Times New Roman", "DejaVu Serif",
        ]
    else:
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "Arial", "Verdana", "DejaVu Sans",
        ]

    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue

    return ImageFont.load_default()


def add_decorative_border(draw: ImageDraw.Draw, size: Tuple[int, int], mood: str) -> None:
    """Add a subtle decorative border."""
    w, h = size
    border_colors = {
        "inspiring": (242, 202, 80, 60),
        "cyberpunk": (180, 0, 255, 50),
        "zen": (100, 150, 80, 40),
        "stoic": (180, 160, 120, 45),
        "philosophical": (100, 120, 200, 40),
    }
    color = border_colors.get(mood.lower(), (255, 255, 255, 35))

    # Double border
    draw.rectangle([30, 30, w - 30, h - 30], outline=color, width=1)
    draw.rectangle([42, 42, w - 42, h - 42], outline=(color[0], color[1], color[2], 20), width=1)

    # Corner accents
    corner_size = 20
    accent_color = (color[0], color[1], color[2], 100)
    for cx, cy in [(30, 30), (w - 30, 30), (30, h - 30), (w - 30, h - 30)]:
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=accent_color)


def overlay_text_advanced(img: Image.Image, quote: str, author: str, mood: str) -> Image.Image:
    """
    Advanced text overlay with dynamic sizing, shadows, and decorative elements.
    """
    draw = ImageDraw.Draw(img, "RGBA")
    W, H = img.size

    # Dynamic font sizing based on quote length
    q_len = len(quote)
    if q_len < 50:
        base_size = 88
    elif q_len < 100:
        base_size = 72
    elif q_len < 180:
        base_size = 58
    elif q_len < 260:
        base_size = 46
    else:
        base_size = 38

    font_quote = load_font(base_size, mood)
    font_author = load_font(int(base_size * 0.48), mood)
    font_levi = load_font(int(base_size * 0.32), mood)

    # Wrap text
    char_width = max(14, min(26, int(W / base_size * 1.5)))
    lines = textwrap.wrap(quote, width=char_width)

    # Calculate line height
    try:
        bbox = font_quote.getbbox("Ay")
        line_h = bbox[3] - bbox[1]
    except AttributeError:
        line_h = base_size + 8
    line_spacing = int(line_h * 1.4)

    author_gap = 60
    levi_gap = 35
    total_h = len(lines) * line_spacing + author_gap + 40
    start_y = (H - total_h) / 2

    # Add decorative border
    add_decorative_border(draw, (W, H), mood)

    # Accent line above quote
    line_w = min(200, W // 3)
    line_color = _get_accent_color(mood, 160)
    draw.line([(W // 2 - line_w // 2, start_y - 30),
               (W // 2 + line_w // 2, start_y - 30)],
              fill=line_color, width=2)

    # Opening quotation mark
    try:
        font_big_quote = load_font(int(base_size * 2), mood)
        draw.text((50, start_y - base_size), "\u201c",
                  fill=(255, 255, 255, 35), font=font_big_quote)
    except Exception:
        pass

    # Draw each line with multi-layer shadow
    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font_quote)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw = len(line) * base_size // 2

        x = (W - tw) / 2
        y = start_y + i * line_spacing

        # Deep shadow layers
        for ox, oy, alpha in [(4, 4, 60), (3, 3, 80), (2, 2, 100), (1, 1, 120)]:
            draw.text((x + ox, y + oy), line, fill=(0, 0, 0, alpha), font=font_quote)

        # Glow layer (subtle)
        glow_color = _get_accent_color(mood, 15)
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + ox, y + oy), line, fill=glow_color, font=font_quote)

        # Main text
        draw.text((x, y), line, fill=(255, 255, 255, 245), font=font_quote)

    # Author attribution
    author_text = f"— {author}" if author and author.lower() not in ["unknown", "levi ai", ""] else "— LEVI AI"
    ay = start_y + len(lines) * line_spacing + author_gap

    try:
        abbox = draw.textbbox((0, 0), author_text, font=font_author)
        aw = abbox[2] - abbox[0]
    except AttributeError:
        aw = len(author_text) * int(base_size * 0.48) // 2

    ax = (W - aw) / 2

    # Decorative line above author
    line_color_author = _get_accent_color(mood, 120)
    draw.line([(W // 2 - 60, ay - 18), (W // 2 + 60, ay - 18)],
              fill=line_color_author, width=1)

    # Author shadow + text
    draw.text((ax + 1, ay + 1), author_text, fill=(0, 0, 0, 100), font=font_author)
    draw.text((ax, ay), author_text,
              fill=_get_accent_color(mood, 220), font=font_author)

    # LEVI AI watermark (bottom right, subtle)
    levi_text = "LEVI AI"
    try:
        lbbox = draw.textbbox((0, 0), levi_text, font=font_levi)
        lw = lbbox[2] - lbbox[0]
    except AttributeError:
        lw = len(levi_text) * int(base_size * 0.32) // 2

    draw.text((W - lw - 35, H - 50), levi_text,
              fill=(255, 255, 255, 50), font=font_levi)

    return img


def _get_accent_color(mood: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Get mood-appropriate accent color."""
    accent_colors = {
        "inspiring":     (242, 202, 80),
        "cyberpunk":     (200, 100, 255),
        "zen":           (100, 200, 120),
        "stoic":         (200, 180, 140),
        "philosophical": (140, 160, 255),
        "calm":          (100, 200, 220),
        "melancholic":   (120, 140, 200),
        "energetic":     (255, 140, 0),
        "mystical":      (180, 100, 255),
        "dark":          (180, 160, 120),
        "futuristic":    (0, 200, 255),
    }
    rgb = accent_colors.get(mood.lower(), (255, 255, 255))
    return (rgb[0], rgb[1], rgb[2], alpha)


def add_watermark(img: Image.Image, user_tier: str = "free") -> Image.Image:
    """Add watermark for free tier."""
    if user_tier != "free":
        return img
    draw = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    font = load_font(18)
    text = "levi-ai.create.app"
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw = len(text) * 9
    # Subtle watermark
    draw.text((W - tw - 20, H - 35), text, fill=(255, 255, 255, 55), font=font)
    return img


# ─────────────────────────────────────────────
# S3 UPLOAD
# ─────────────────────────────────────────────

# S3 upload moved to s3_utils.py


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def generate_quote_image(
    quote: str,
    author: str = "",
    mood: str = "neutral",
    size: Tuple[int, int] = (1024, 1024),
    custom_bg: str = "",
    user_tier: str = "free",
    style: str = "",
    return_pil: bool = False,
    upload_to_s3: bool = False,
    user_id: Optional[int] = None,
) -> Any:
    """
    Generate a complete quote image with AI background and text overlay.

    Returns BytesIO (default), PIL Image (return_pil=True),
    or dict with url+BytesIO if upload_to_s3=True.
    """
    # ── Step 1: Get background ──
    bg: Optional[Image.Image] = None

    # Custom upload (base64 only — no SSRF)
    if custom_bg and custom_bg.startswith("data:image"):
        try:
            _, encoded = custom_bg.split(",", 1)
            bg = Image.open(BytesIO(base64.b64decode(encoded))).convert("RGBA")
            if bg.size != size:
                bg = bg.resize(size, Image.Resampling.LANCZOS)
            logger.info("Using custom background")
        except Exception as e:
            logger.warning(f"Custom bg failed: {e}")
            bg = None

    # Try local SD engine first (GPU)
    if bg is None:
        try:
            try:
                from backend.sd_engine import generate as sd_generate  # type: ignore
            except ImportError:
                from sd_engine import generate as sd_generate  # type: ignore
            prompt = build_prompt(quote, mood, style)
            sd_result = sd_generate(prompt, style=style or "default", size=size, enhance=False)
            if sd_result:
                bg = Image.open(sd_result).convert("RGBA")
                logger.info("Using SD engine background")
        except Exception as e:
            logger.debug(f"SD engine not available: {e}")

    # Together AI FLUX (primary cloud)
    if bg is None and TOGETHER_API_KEY:
        try:
            prompt = build_prompt(quote, mood, style, enhance=True)
            logger.info(f"Together AI generating: '{prompt[:60]}...'")
            bg = generate_via_together(prompt, size)
            logger.info("Using Together AI background")
        except Exception as e:
            logger.error(f"Together AI failed: {e}")

    # PIL gradient fallback
    if bg is None:
        logger.info("Using gradient fallback")
        bg = generate_gradient_fallback(mood, size)

    # ── Step 2: Compositing ──
    bg = add_dark_overlay(bg, mood)
    bg = overlay_text_advanced(bg, quote, author, mood)
    bg = add_vignette(bg)
    bg = add_watermark(bg, user_tier)

    # Final enhancement
    enhancer = ImageEnhance.Sharpness(bg)
    bg = enhancer.enhance(1.1)
    bg = bg.filter(ImageFilter.SMOOTH)

    if return_pil:
        return bg

    # ── Step 3: Export ──
    output = BytesIO()
    bg.convert("RGB").save(output, "PNG", optimize=True, quality=95)
    output.seek(0)

    # Optional S3 upload
    if upload_to_s3 and AWS_S3_BUCKET:
        img_bytes = output.getvalue()
        s3_url = upload_image_to_s3(img_bytes, user_id)
        output.seek(0)
        if s3_url:
            return {"url": s3_url, "bio": output}

    return output


# Convenience alias
def generate_image(
    prompt: str,
    mood: str = "neutral",
    size: Tuple[int, int] = (1024, 1024),
    **kwargs
) -> BytesIO:
    """Simple alias for direct prompt-based generation."""
    return generate_quote_image(prompt, mood=mood, size=size, **kwargs)
