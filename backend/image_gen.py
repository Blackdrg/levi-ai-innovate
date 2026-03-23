import os
from typing import Any
import requests # type: ignore
import base64
import random
import textwrap
import math
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance # type: ignore
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, wait_fixed # type: ignore

logger = logging.getLogger(__name__)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_API_URL = "https://api.together.xyz/v1/images/generations"

# PIL Decompression Bomb protection
Image.MAX_IMAGE_PIXELS = 50_000_000

# ─────────────────────────────────────────────
# 1. Generate background image via Together.AI
# ─────────────────────────────────────────────

MOOD_PROMPTS = {
    "inspiring":     "golden sunrise over mountain peaks, divine light rays, epic sky, cinematic, 4k",
    "calm":          "serene zen garden with still water reflection, soft mist, peaceful, minimalist",
    "energetic":     "electric storm over a neon city, dynamic motion blur, vibrant colors, dramatic",
    "philosophical": "deep space nebula with galaxies, cosmic dust, infinite universe, dark ethereal",
    "melancholic":   "rainy cobblestone street at night, soft bokeh lights, moody, cinematic blue tones",
    "stoic":         "ancient marble columns at dawn, stone texture, classical architecture, muted tones",
    "zen":           "bamboo forest with morning light rays, green tranquility, japanese aesthetic",
    "cyberpunk":     "neon-lit cyberpunk city at night, holographic signs, rain reflections, purple glow",
    "futuristic":    "sleek futuristic space station interior, clean white surfaces, blue ambient light",
    "neutral":       "abstract flowing gradients, soft bokeh, artistic blur, pastel tones",
}

def build_prompt(quote: str, mood: str) -> str:
    """Build a rich image prompt from mood + key quote words."""
    base = MOOD_PROMPTS.get(mood.lower(), MOOD_PROMPTS["neutral"])
    # Extract 2-3 meaningful words from the quote to add context
    stop_words = {"the","a","an","is","are","to","of","and","or","in","it","you","we","i","me"}
    words = [w.strip(".,!?\"'") for w in quote.lower().split() if w not in stop_words and len(w) > 3]
    top_words = []
    for i, w in enumerate(words):
        if i < 2: top_words.append(w)
    keywords = " ".join(top_words) if words else ""
    return f"{base}, {keywords}, no text, no words, wallpaper quality, ultra detailed"

def together_retry_logic(retry_state):
    """Custom retry logic for Together AI 429 Retry-After header."""
    if retry_state.outcome.failed:
        exc = retry_state.outcome.exception()
        if isinstance(exc, requests.exceptions.HTTPError) and exc.response.status_code == 429:
            retry_after = exc.response.headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
    return wait_exponential(multiplier=1, min=2, max=10)(retry_state)

@retry(
    stop=stop_after_attempt(3),
    wait=together_retry_logic,
    retry=retry_if_exception_type((requests.exceptions.RequestException, Exception)),
    reraise=True
)
def generate_background_together(prompt: str, size: tuple = (1024, 1024)) -> Image.Image:
    """Call Together.AI FLUX API to generate background image."""
    if not TOGETHER_API_KEY:
        raise ValueError("TOGETHER_API_KEY environment variable is not set.")

    payload = {
        "model": "black-forest-labs/FLUX.1-schnell",
        "prompt": prompt,
        "width": size[0],
        "height": size[1],
        "steps": 4,          # schnell works great at 4 steps
        "n": 1,
        "disable_safety_checker": False,
        "response_format": "b64_json"
    }

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(TOGETHER_API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # Decode base64 image
        img_b64 = data["data"][0]["b64_json"]
        img_bytes = base64.b64decode(img_b64)
        img = Image.open(BytesIO(img_bytes)).convert("RGBA")

        if img.size != size:
            from PIL import ImageOps  # type: ignore
            img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
        return img

    except Exception as e:
        logger.error(f"[Together.AI] Image generation failed: {e}")
        raise e


# ─────────────────────────────────────────────
# 2. Fallback: gradient background (no API)
# ─────────────────────────────────────────────

def generate_gradient_fallback(mood: str, size: tuple) -> Image.Image:
    mood_colors = {
        "inspiring":     [(40, 0, 80),   (100, 40, 180)],
        "calm":          [(10, 40, 50),  (40, 120, 130)],
        "energetic":     [(80, 0, 20),   (200, 60, 40)],
        "philosophical": [(10, 10, 30),  (50, 50, 90)],
        "melancholic":   [(5, 10, 30),   (30, 40, 100)],
        "stoic":         [(30, 30, 30),  (100, 100, 100)],
        "zen":           [(30, 50, 20),  (100, 140, 60)],
        "cyberpunk":     [(20, 0, 40),   (180, 0, 255)],
        "futuristic":    [(0, 10, 40),   (0, 200, 255)],
        "neutral":       [(20, 30, 50),  (60, 80, 120)],
    }
    colors = mood_colors.get(mood.lower(), mood_colors["neutral"])
    base = Image.new("RGBA", size, colors[0] + (255,))
    top  = Image.new("RGBA", size, colors[1] + (255,))
    mask = Image.new("L", size)
    d = ImageDraw.Draw(mask)
    for y in range(size[1]):
        d.line([(0, y), (size[0], y)], fill=int(255 * y / size[1]))
    return Image.composite(top, base, mask)


# ─────────────────────────────────────────────
# 3. Composite: overlay dark layer + add text
# ─────────────────────────────────────────────

def add_dark_overlay(img: Image.Image, mood: str) -> Image.Image:
    opacity = 160 if mood.lower() in ["philosophical", "melancholic", "cyberpunk"] else 130
    overlay = Image.new("RGBA", img.size, (0, 0, 0, opacity))
    return Image.alpha_composite(img, overlay)


def add_vignette(img: Image.Image) -> Image.Image:
    vignette = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(vignette)
    for i in range(150):
        alpha = int(120 * (1 - i / 150))
        d.rectangle([i, i, img.size[0]-i, img.size[1]-i], outline=(0, 0, 0, alpha), width=1)
    return Image.alpha_composite(img, vignette)


def add_watermark(img: Image.Image, user_tier: str = "free") -> Image.Image:
    """Add a watermark for free-tier users."""
    if user_tier == "free":
        draw = ImageDraw.Draw(img, "RGBA")
        W, H = img.size
        font = load_font(22)
        
        text = "Made with LEVI AI"
        bbox = draw.textbbox((0, 0), text, font=font) if hasattr(draw, "textbbox") else (0, 0, 150, 24)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        # Bottom right with semi-transparent background
        rect = [W - tw - 60, H - th - 60, W - 30, H - 30]
        draw.rectangle(rect, fill=(0, 0, 0, 80))
        draw.text((W - tw - 45, H - th - 45), text, fill=(255, 255, 255, 120), font=font)
    return img


def load_font(size: int, mood: str = ""):
    serif_fonts   = ["Georgia", "Times New Roman", "DejaVu Serif", "FreeSerif"]
    sans_fonts    = ["Arial", "Verdana", "DejaVu Sans", "FreeSans"]
    prefer_serif  = mood.lower() in ["philosophical", "stoic", "zen", "melancholic", "calm"]
    font_list     = serif_fonts if prefer_serif else sans_fonts

    for name in font_list:
        try:
            return ImageFont.truetype(name, size)
        except:
            continue
    return ImageFont.load_default()


def overlay_text(img: Image.Image, quote: str, author: str, mood: str) -> Image.Image:
    draw = ImageDraw.Draw(img, "RGBA")
    W, H = img.size

    # Dynamic font size
    if   len(quote) < 60:  base_size = 82
    elif len(quote) < 120: base_size = 68
    elif len(quote) < 200: base_size = 56
    else:                  base_size = 46

    font_quote  = load_font(base_size, mood)
    font_author = load_font(int(base_size * 0.55), mood)

    # Wrap text
    char_width = max(16, min(28, int(W / base_size * 1.6)))
    lines = textwrap.wrap(quote, width=char_width)

    line_h      = font_quote.getbbox("Ay")[3] - font_quote.getbbox("Ay")[1] if hasattr(font_quote, "getbbox") else base_size + 10
    line_spacing = int(line_h * 1.35)
    author_gap   = 80
    total_h      = len(lines) * line_spacing + author_gap
    start_y      = (H - total_h) / 2

    # Draw each line
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_quote) if hasattr(draw, "textbbox") else (0, 0, W//2, base_size)
        tw = bbox[2] - bbox[0]
        x  = (W - tw) / 2
        y  = start_y + i * line_spacing

        # Shadow layers
        for ox, oy in [(2, 2), (3, 3), (4, 4)]:
            draw.text((x + ox, y + oy), line, fill=(0, 0, 0, 80), font=font_quote)
        # Main text
        draw.text((x, y), line, fill=(255, 255, 255, 255), font=font_quote)

    # Author line
    author_text = f"— {author}" if author else "— LEVI AI"
    abbox = draw.textbbox((0, 0), author_text, font=font_author) if hasattr(draw, "textbbox") else (0, 0, 200, 30)
    aw    = abbox[2] - abbox[0]
    ay    = start_y + len(lines) * line_spacing + 40

    # Decorative line above author
    draw.line([(W/2 - 50, ay - 16), (W/2 + 50, ay - 16)], fill=(255, 255, 255, 120), width=2)
    draw.text(((W - aw) / 2, ay), author_text, fill=(255, 255, 255, 200), font=font_author)

    # Border frames
    draw.rectangle([40, 40, W-40, H-40], outline=(255, 255, 255, 40), width=2)
    draw.rectangle([55, 55, W-55, H-55], outline=(255, 255, 255, 15), width=1)

    return img


# ─────────────────────────────────────────────
# 4. Main entry point (called by main.py)
# ─────────────────────────────────────────────

def generate_quote_image(
    quote:     str,
    author:    str   = "",
    mood:      str   = "neutral",
    size:      tuple = (1024, 1024),
    custom_bg: str   = "",
    user_tier: str   = "free",
    return_pil: bool = False
) -> Any:

    # --- Step 1: Get background ---
    bg = None

    # Custom upload takes priority
    if custom_bg:
        try:
            # Only base64 data-URIs are accepted — HTTP URLs are rejected upstream
            # to prevent Server-Side Request Forgery (SSRF).
            if custom_bg.startswith("data:image"):
                _, encoded = custom_bg.split(",", 1)
                bg = Image.open(BytesIO(base64.b64decode(encoded))).convert("RGBA")
            if bg and bg.size != size:
                bg = bg.resize(size, Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[custom_bg] Failed: {e}")
            bg = None

    # Primary: SD Engine (local SD or Together AI fallback)
    if bg is None:
        try:
            from backend.sd_engine import generate as sd_generate  # type: ignore
        except ImportError:
            from sd_engine import generate as sd_generate  # type: ignore
        prompt = build_prompt(quote, mood)
        style = getattr(generate_quote_image, '_current_style', 'default')
        sd_result = sd_generate(prompt, style=style, size=size, enhance=True)
        if sd_result:
            bg = Image.open(sd_result).convert("RGBA")

    # Legacy Together.AI generation (if sd_engine returned None)
    if bg is None and TOGETHER_API_KEY:
        prompt = build_prompt(quote, mood)
        print(f"[Together.AI] Prompt: {prompt}")
        bg = generate_background_together(prompt, size)


    # Fallback to gradient if API fails or key missing
    if bg is None:
        print("[Fallback] Using gradient background")
        bg = generate_gradient_fallback(mood, size)

    # --- Step 2: Dark overlay so text is readable ---
    bg = add_dark_overlay(bg, mood)

    # --- Step 3: Overlay quote text ---
    bg = overlay_text(bg, quote, author, mood)

    # --- Step 4: Vignette + final polish ---
    bg = add_vignette(bg)
    bg = add_watermark(bg, user_tier)
    bg = bg.filter(ImageFilter.SHARPEN)

    # --- Step 5: Export ---
    if return_pil:
        return bg

    output = BytesIO()
    bg.convert("RGB").save(output, "PNG", optimize=True)
    output.seek(0)
    return output