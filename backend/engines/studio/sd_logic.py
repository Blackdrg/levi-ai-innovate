# backend/engines/studio/sd_logic.py
import os
import logging
import threading
from io import BytesIO
from typing import Optional, Any

logger = logging.getLogger(__name__)

def _truncate(s: str, n: int) -> str:
    result = ""
    for i, ch in enumerate(s):
        if i >= n: break
        result += ch
    return result

STYLE_PRESETS = {
    "cinematic": {
        "suffix": "cinematic lighting, film grain, anamorphic lens flare, dramatic shadows, 35mm film look, depth of field, golden hour, movie still, 8k",
        "negative": "cartoon, anime, drawing, painting, ugly, blurry",
    },
    "anime": {
        "suffix": "anime style, studio ghibli, vibrant colors, detailed illustration, cel shading, manga aesthetic, clean lines, high quality anime art",
        "negative": "photorealistic, photograph, 3d render, ugly, blurry",
    },
    "philosophical_art": {
        "suffix": "classical oil painting, chiaroscuro, renaissance style, symbolic, allegorical, deep shadows, museum quality, fine art, rembrandt lighting",
        "negative": "cartoon, anime, modern, neon, ugly, blurry",
    },
    "photorealistic": {
        "suffix": "photorealistic, DSLR photography, sharp focus, natural lighting, high resolution, professional photograph, 8k uhd, detailed",
        "negative": "cartoon, anime, painting, drawing, illustration, ugly",
    },
    "oil_painting": {
        "suffix": "oil painting on canvas, thick brushstrokes, impasto technique, impressionist, rich textures, warm palette, gallery quality, fine art",
        "negative": "photograph, 3d render, cartoon, anime, digital art, ugly",
    },
    "cyberpunk": {
        "suffix": "cyberpunk aesthetic, neon lights, rain-slicked streets, holographic, futuristic cityscape, purple and cyan glow, blade runner style, 8k",
        "negative": "natural, daylight, pastoral, rustic, ugly, blurry",
    },
    "watercolor": {
        "suffix": "watercolor painting, soft washes of color, wet-on-wet technique, translucent layers, artistic, dreamlike, paper texture, fine art illustration",
        "negative": "photograph, 3d render, sharp edges, cartoon, dark, ugly, blurry",
    },
    "surrealism": {
        "suffix": "surrealist painting, dreamlike, impossible geometry, melting clocks, salvador dali inspired, symbolic, hyper-detailed, strange beauty, 4k",
        "negative": "photograph, realistic, mundane, ugly, blurry, low quality",
    },
    "minimal_line_art": {
        "suffix": "minimalist line art, clean strokes, single continuous line, black and white, negative space, elegant simplicity, graphic design, vector aesthetic",
        "negative": "color, photorealistic, painting, messy, cluttered, blurry",
    },
    "default": {
        "suffix": "high quality, detailed, beautiful, artistic, 4k",
        "negative": "ugly, blurry, deformed, low quality",
    },
}

def enhance_prompt(base_prompt: str, style: str = "default") -> str:
    from backend.utils.network import groq_breaker
    import groq # type: ignore
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return base_prompt

    client = groq.Groq(api_key=api_key)
    try:
        response = groq_breaker.call(
            client.chat.completions.create,
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "system",
                "content": f"You are an expert image prompt engineer for Stable Diffusion. Style: {style}. Output ONLY the enhanced prompt."
            }, {"role": "user", "content": f"Expand this: {base_prompt}"}],
            max_tokens=180,
            temperature=0.75,
        )
        enhanced = response.choices[0].message.content.strip()
        logger.info(f"[SD Logic] Enhanced prompt: {enhanced[:50]}...")
        return enhanced
    except Exception as e:
        logger.warning(f"Prompt enhancement failed: {e}")
        return base_prompt

_sd_pipe = None
_sd_lock = threading.Lock()
_sd_available = None

def _load_sd_pipeline():
    global _sd_pipe, _sd_available
    if _sd_available is False: return None
    with _sd_lock:
        if _sd_pipe: return _sd_pipe
        try:
            import torch # type: ignore
            if not torch.cuda.is_available():
                _sd_available = False
                return None
            from diffusers import StableDiffusionPipeline # type: ignore
            model_id = os.getenv("SD_MODEL_ID", "runwayml/stable-diffusion-v1-5")
            _sd_pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16).to("cuda")
            _sd_available = True
            return _sd_pipe
        except Exception as e:
            logger.warning(f"SD Initialization failed: {e}")
            _sd_available = False
            return None

def generate_image_logic(prompt: str, style: str = "default", size: tuple = (1024, 1024), enhance: bool = True):
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["default"])
    if enhance: prompt = enhance_prompt(prompt, style)
    full_prompt = f"{prompt}, {style_config['suffix']}"
    
    pipe = _load_sd_pipeline()
    if pipe:
        try:
            import torch # type: ignore
            with torch.no_grad():
                image = pipe(prompt=full_prompt, negative_prompt=style_config["negative"], width=512, height=512).images[0]
                if size != (512, 512):
                    from PIL import Image # type: ignore
                    image = image.resize(size, Image.Resampling.LANCZOS)
                buf = BytesIO()
                image.save(buf, format="PNG")
                buf.seek(0)
                return buf
        except Exception as e:
            logger.error(f"Local SD failed: {e}")

    return _generate_via_together(full_prompt, size)

def _generate_via_together(prompt, size):
    import requests # type: ignore
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key: return None
    try:
        import base64
        from PIL import Image # type: ignore
        resp = requests.post("https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "black-forest-labs/FLUX.1-schnell", "prompt": prompt, "width": size[0], "height": size[1], "response_format": "b64_json"}
        )
        img_b64 = resp.json()["data"][0]["b64_json"]
        img = Image.open(BytesIO(base64.b64decode(img_b64))).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Together AI failed: {e}")
        return None
