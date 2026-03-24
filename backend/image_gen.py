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
    """Build a rich image prompt from mood + key quote words using Groq if available."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
            import groq # type: ignore
            client = groq.Groq(api_key=groq_api_key)
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a midjourney prompt engineer. Take the quote and mood, and write a vivid, cinematic, highly detailed 1-sentence image description. NO TEXT, no words in the image. Wallpaper quality."},
                    {"role": "user", "content": f"Quote: '{quote}'\nMood: {mood}"}
                ],
                max_tokens=60,
                temperature=0.8
            )
            enhanced = resp.choices[0].message.content.strip()
            return f"{enhanced}, no text, no words, ultra detailed, wallpaper quality"
        except Exception as e:
            logger.warning(f"Groq prompt enhancement failed: {e}")

    base = MOOD_PROMPTS.get(mood.lower(), MOOD_PROMPTS["neutral"])
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
        "inspiring":     [(20, 0, 40),   (100, 40, 150), (255, 150, 50)],
        "calm":          [(5, 20, 30),  (20, 80, 100),  (100, 200, 220)],
        "energetic":     [(40, 0, 10),   (150, 20, 20),  (255, 100, 0)],
        "philosophical": [(5, 5, 15),  (30, 20, 60),  (80, 70, 120)],
        "melancholic":   [(5, 5, 20),   (20, 30, 80),   (60, 80, 120)],
        "stoic":         [(15, 15, 15),  (60, 60, 60),  (120, 120, 120)],
        "zen":           [(10, 30, 10),  (50, 100, 40), (120, 180, 80)],
        "cyberpunk":     [(20, 0, 40),   (100, 0, 150),   (0, 255, 255)],
        "futuristic":    [(0, 5, 20),   (0, 100, 200),  (0, 250, 255)],
        "romantic":      [(40, 0, 20),   (180, 40, 80),  (255, 120, 150)],
        "dark":          [(0, 0, 5),     (15, 10, 10),   (40, 20, 20)],
        "neutral":       [(10, 15, 25),  (40, 50, 80),  (100, 120, 160)],
    }
    colors = mood_colors.get(mood.lower(), mood_colors["neutral"])
    base = Image.new("RGBA", size, colors[0] + (255,))
    mid  = Image.new("RGBA", size, colors[1] + (255,))
    top  = Image.new("RGBA", size, colors[2] + (255,))
    
    mask1 = Image.new("L", size)
    d1 = ImageDraw.Draw(mask1)
    half_h = size[1] // 2
    for y in range(half_h):
        d1.line([(0, y), (size[0], y)], fill=int(255 * (y / half_h)))
    
    mask2 = Image.new("L", size)
    d2 = ImageDraw.Draw(mask2)
    for y in range(half_h, size[1]):
        val = int(255 * ((y - half_h) / half_h))
        d2.line([(0, y), (size[0], y)], fill=val)
        d1.line([(0, y), (size[0], y)], fill=255)
    
    step1 = Image.composite(mid, base, mask1)
    return Image.composite(top, step1, mask2)


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
    W, H = img.size

    # Dynamic font size (38-88px mapped over 20-300 chars)
    length = len(quote)
    base_size = int(max(38.0, min(88.0, 88.0 - (length - 20) * (50.0 / 280.0))))

    font_quote  = load_font(base_size, mood)
    font_author = load_font(int(base_size * 0.55), mood)
    font_big    = load_font(int(base_size * 2.5), mood)

    char_width = int(max(16.0, min(32.0, W / base_size * 1.6)))
    lines = textwrap.wrap(quote, width=char_width)

    line_h      = font_quote.getbbox("Ay")[3] - font_quote.getbbox("Ay")[1] if hasattr(font_quote, "getbbox") else base_size + 10
    line_spacing = int(line_h * 1.35)
    author_gap   = 80
    total_h      = len(lines) * line_spacing + author_gap
    start_y      = (H - total_h) / 2

    txt_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_layer)
    accent = (255, 200, 100, 180) if mood == "inspiring" else (100, 200, 255, 180) if mood in ["calm", "cyberpunk"] else (255, 255, 255, 150)

    # Large quote marks
    txt_draw.text((60, start_y - int(base_size)), '"', fill=accent, font=font_big)

    for i, line in enumerate(lines):
        bbox = txt_draw.textbbox((0, 0), line, font=font_quote) if hasattr(txt_draw, "textbbox") else (0, 0, W//2, base_size)
        tw = bbox[2] - bbox[0]
        x  = (W - tw) / 2
        y  = start_y + i * line_spacing
        
        # Glow & Deep shadow happens via filter, here we just draw core and standard shadow
        txt_draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 200), font=font_quote)
        txt_draw.text((x, y), line, fill=(255, 255, 255, 255), font=font_quote)

    author_text = f"— {author}" if author else "— LEVI AI"
    abbox = txt_draw.textbbox((0, 0), author_text, font=font_author) if hasattr(txt_draw, "textbbox") else (0, 0, 200, 30)
    aw    = abbox[2] - abbox[0]
    ay    = start_y + len(lines) * line_spacing + 40

    txt_draw.line([(W/2 - 50, ay - 16), (W/2 + 50, ay - 16)], fill=accent, width=2)
    txt_draw.text(((W - aw) / 2, ay), author_text, fill=(255, 255, 255, 200), font=font_author)

    # Filter glow layer
    glow_layer = txt_layer.filter(ImageFilter.GaussianBlur(radius=6))
    img = Image.alpha_composite(img, glow_layer)
    img = Image.alpha_composite(img, txt_layer)

    # Complex Border frames
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle([40, 40, W-40, H-40], outline=accent, width=2)
    draw.rectangle([55, 55, W-55, H-55], outline=(255, 255, 255, 20), width=1)
    # Corner accents
    d = 30
    draw.line([(35, 35), (35+d, 35)], fill=accent, width=4)
    draw.line([(35, 35), (35, 35+d)], fill=accent, width=4)

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
    return_pil: bool = False,
    user_id:   int   = 0
) -> Any:

    # --- Step 1: Get background ---
    bg = None

    if custom_bg:
        try:
            if custom_bg.startswith("data:image"):
                _, encoded = custom_bg.split(",", 1)
                bg = Image.open(BytesIO(base64.b64decode(encoded))).convert("RGBA")
            if bg and bg.size != size:
                bg = bg.resize(size, Image.Resampling.LANCZOS)
        except Exception as e:
            logger.warning(f"[custom_bg] Failed: {e}")
            bg = None

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

    if bg is None and TOGETHER_API_KEY:
        prompt = build_prompt(quote, mood)
        bg = generate_background_together(prompt, size)

    if bg is None:
        bg = generate_gradient_fallback(mood, size)

    # --- Step 2: Dark overlay so text is readable ---
    bg = add_dark_overlay(bg, mood)

    # --- Step 3: Overlay quote text ---
    bg = overlay_text(bg, quote, author, mood)

    # --- Step 4: Vignette + final polish ---
    bg = add_vignette(bg)
    bg = add_watermark(bg, user_tier)
    bg = bg.filter(ImageFilter.SHARPEN)

    if return_pil:
        return bg
        
    output = BytesIO()
    bg.convert("RGB").save(output, "PNG", optimize=True)
    
    # --- Step 5: S3 Upload Integration ---
    if os.getenv("AWS_S3_BUCKET"):
        try:
            import boto3 # type: ignore
            import uuid
            s3 = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            bucket = os.getenv("AWS_S3_BUCKET")
            filename = f"images/{user_id}/{uuid.uuid4().hex}.png"
            output.seek(0)
            s3.put_object(Bucket=bucket, Key=filename, Body=output.getvalue(), ContentType="image/png")
            
            cloudfront = os.getenv("CLOUDFRONT_DOMAIN")
            if cloudfront:
                return f"https://{cloudfront}/{filename}"
            return s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": filename}, ExpiresIn=604800)
        except Exception as e:
            logger.error(f"S3 Direct Upload failed: {e}")

    output.seek(0)
    return output