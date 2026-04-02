import os
import logging
import threading
import asyncio
from io import BytesIO
from typing import Optional, Any, Dict, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

STYLE_PRESETS = {
    "cinematic": {
        "suffix": "cinematic lighting, film grain, anamorphic lens flare, dramatic shadows, 35mm film look, 8k",
        "negative": "cartoon, anime, blurry, low quality",
    },
    "anime": {
        "suffix": "anime style, studio ghibli, vibrant colors, detailed illustration, cel shading, high quality anime art",
        "negative": "photorealistic, 3d render, ugly, blurry",
    },
    "cyberpunk": {
        "suffix": "cyberpunk aesthetic, neon lights, holographic, futuristic cityscape, blade runner style, 8k",
        "negative": "natural, pastoral, sunlight, rustic",
    },
    "photorealistic": {
        "suffix": "photorealistic, DSLR photography, sharp focus, natural lighting, high resolution, 8k uhd",
        "negative": "cartoon, painting, illustration, ugly",
    },
    "surreal": {
        "suffix": "surrealist painting, dreamlike, impossible geometry, symbolic, hyper-detailed, strange beauty",
        "negative": "photograph, mundane, realistic",
    },
    "vaporwave": {
        "suffix": "vaporwave aesthetic, pink and teal, 80s retro, glitch art, low-poly, nostalgic",
        "negative": "sharp, high-contrast, modern",
    }
}

class StudioGenerator:
    """
    Sovereign Studio Engine.
    Handles visual synthesis and multi-modal creative generation.
    """
    
    def __init__(self):
        self._pipe = None
        self._lock = threading.Lock()
        self.together_api_key = os.getenv("TOGETHER_API_KEY")

    async def generate_image(self, prompt: str, style: str = "default", size: Tuple[int, int] = (1024, 1024), enhance: bool = True) -> Optional[BytesIO]:
        """
        Synthesizes an image using the best available local or remote engine.
        """
        logger.info(f"Synthesizing visual: {prompt[:30]}... [Style: {style}]")
        
        style_config = STYLE_PRESETS.get(style, STYLE_PRESETS.get("cinematic"))
        final_prompt = f"{prompt}, {style_config['suffix']}"
        negative_prompt = style_config["negative"]

        # 1. Attempt Local Diffusion (CUDA required)
        # Placeholder for local torch/diffusers logic (Phase 48 upgrade)
        
        # 2. Universal API Fallback (Together AI / Flux)
        return await self._generate_via_together(final_prompt, negative_prompt, size)

    async def _generate_via_together(self, prompt: str, negative: str, size: Tuple[int, int]) -> Optional[BytesIO]:
        """High-fidelity generation via Together Flux API."""
        if not self.together_api_key:
            logger.error("Together API Key missing for Studio Engine.")
            return None
            
        try:
            import requests, base64
            loop = asyncio.get_event_loop()
            
            payload = {
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": prompt,
                "width": size[0],
                "height": size[1],
                "steps": 4,
                "response_format": "b64_json"
            }
            
            headers = {"Authorization": f"Bearer {self.together_api_key}"}
            
            def _call():
                return requests.post("https://api.together.xyz/v1/images/generations", json=payload, headers=headers, timeout=30)
            
            resp = await loop.run_in_executor(None, _call)
            data = resp.json()
            
            if "data" in data:
                img_b64 = data["data"][0]["b64_json"]
                img_data = base64.b64decode(img_b64)
                buf = BytesIO(img_data)
                buf.seek(0)
                return buf
                
        except Exception as e:
            logger.error(f"Studio generation failure: {e}")
            
        return None
