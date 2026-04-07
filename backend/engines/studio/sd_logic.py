import os
import logging
import threading
import asyncio
from io import BytesIO
import json
from typing import Optional, Tuple
from backend.core.executor.streams import StreamManager
from backend.db.redis import r_async, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

# Local backend URLs (configurable via env)
COMFYUI_URL   = os.getenv("COMFYUI_URL",   "http://localhost:8188")
SDWEBUI_URL   = os.getenv("SDWEBUI_URL",   "http://localhost:7860")

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
    },
}

class StudioGenerator:
    """
    Sovereign Studio Engine v9.
    Backend waterfall: ComfyUI (local SDXL) → SD-WebUI (local) → Together AI (cloud Flux).
    """

    def __init__(self):
        self._pipe = None
        self._lock = threading.Lock()
        self.together_api_key = os.getenv("TOGETHER_API_KEY")
        self.streams = StreamManager()
        self.is_distributed = os.getenv("DISTRIBUTED_MODE", "false").lower() == "true"

    async def generate_image(
        self,
        prompt: str,
        style: str = "cinematic",
        size: Tuple[int, int] = (1024, 1024),
        enhance: bool = True,
    ) -> Optional[BytesIO]:
        """
        Synthesises an image using the best available backend.
        Hybrid (v2.1): Local Small (Fast) Path <-> DCN Heavy Swarm.
        """
        logger.info("Synthesising visual: %s… [Style: %s, Size: %dx%d]", prompt[:30], style, *size)

        # 🚀 Audit Point: Hybrid Logic (DCN v2.1)
        is_heavy = (size[0] > 512 or size[1] > 512 or enhance)
        
        if self.is_distributed and is_heavy:
            logger.info("📦 [Studio] Heavy task detected. Offloading to DCN Swarm...")
            result = await self._offload_to_dcn_studio(prompt, style, size, enhance)
            if result:
                return result
            logger.warning("[Studio] DCN offload returned no result. Falling back to Local Waterfall.")

        style_config   = STYLE_PRESETS.get(style, STYLE_PRESETS["cinematic"])
        final_prompt   = f"{prompt}, {style_config['suffix']}"
        negative_prompt = style_config["negative"]

        # 1. ComfyUI (local SDXL)
        result = await self._generate_via_comfyui(final_prompt, negative_prompt, size)
        if result:
            return result

        # 2. SD-WebUI txt2img API
        result = await self._generate_via_sdwebui(final_prompt, negative_prompt, size)
        if result:
            return result

        # 3. Together AI / Flux (cloud)
        return await self._generate_via_together(final_prompt, negative_prompt, size)

    # ------------------------------------------------------------------
    # Backend: ComfyUI
    # ------------------------------------------------------------------

    async def _generate_via_comfyui(
        self, prompt: str, negative: str, size: Tuple[int, int]
    ) -> Optional[BytesIO]:
        """
        Submits a simple SDXL prompt to a running ComfyUI instance.
        Uses the /prompt endpoint with a basic latent-image workflow.
        """
        import aiohttp
        import uuid

        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42, "steps": 20, "cfg": 7.0,
                    "sampler_name": "euler_ancestral", "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
            "5": {"class_type": "EmptyLatentImage",
                  "inputs": {"batch_size": 1, "width": size[0], "height": size[1]}},
            "6": {"class_type": "CLIPTextEncode",
                  "inputs": {"clip": ["4", 1], "text": prompt}},
            "7": {"class_type": "CLIPTextEncode",
                  "inputs": {"clip": ["4", 1], "text": negative}},
            "8": {"class_type": "VAEDecode",
                  "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage",
                  "inputs": {"images": ["8", 0], "filename_prefix": "levi_"}},
        }
        client_id = str(uuid.uuid4())

        try:
            timeout = aiohttp.ClientTimeout(total=90)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Submit prompt
                async with session.post(
                    f"{COMFYUI_URL}/prompt",
                    json={"prompt": workflow, "client_id": client_id},
                ) as r:
                    if r.status != 200:
                        logger.debug("[ComfyUI] Submit failed: %d", r.status)
                        return None
                    data = await r.json()
                    prompt_id = data.get("prompt_id")

                if not prompt_id:
                    return None

                # Poll history
                for _ in range(45):   # up to 90 s
                    await asyncio.sleep(2)
                    async with session.get(f"{COMFYUI_URL}/history/{prompt_id}") as r:
                        hist = await r.json()
                    if prompt_id in hist:
                        outputs = hist[prompt_id].get("outputs", {})
                        for node_outputs in outputs.values():
                            for img_meta in node_outputs.get("images", []):
                                fname    = img_meta["filename"]
                                subfolder = img_meta.get("subfolder", "")
                                async with session.get(
                                    f"{COMFYUI_URL}/view",
                                    params={"filename": fname, "subfolder": subfolder, "type": "output"},
                                ) as img_r:
                                    if img_r.status == 200:
                                        buf = BytesIO(await img_r.read())
                                        buf.seek(0)
                                        logger.info("[ComfyUI] Image retrieved: %s", fname)
                                        return buf
                        return None  # outputs exist but no image node found

        except Exception as exc:
            logger.debug("[ComfyUI] Attempt failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Backend: Automatic1111 SD-WebUI
    # ------------------------------------------------------------------

    async def _generate_via_sdwebui(
        self, prompt: str, negative: str, size: Tuple[int, int]
    ) -> Optional[BytesIO]:
        """Calls the SD-WebUI /sdapi/v1/txt2img endpoint."""
        import aiohttp
        import base64

        payload = {
            "prompt":          prompt,
            "negative_prompt": negative,
            "width":           size[0],
            "height":          size[1],
            "steps":           20,
            "cfg_scale":       7.0,
            "sampler_name":    "Euler a",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=90)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{SDWEBUI_URL}/sdapi/v1/txt2img", json=payload) as r:
                    if r.status != 200:
                        logger.debug("[SD-WebUI] Non-200: %d", r.status)
                        return None
                    data = await r.json()
                    images = data.get("images", [])
                    if not images:
                        return None
                    img_data = base64.b64decode(images[0])
                    buf = BytesIO(img_data)
                    buf.seek(0)
                    logger.info("[SD-WebUI] Image generated successfully.")
                    return buf
        except Exception as exc:
            logger.debug("[SD-WebUI] Attempt failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Backend: Together AI / Flux (cloud)
    # ------------------------------------------------------------------

    async def _generate_via_together(
        self, prompt: str, negative: str, size: Tuple[int, int]
    ) -> Optional[BytesIO]:
        """High-fidelity generation via Together Flux API."""
        if not self.together_api_key:
            logger.error("[Together] API Key missing — Studio Engine has no remaining backends.")
            return None

        try:
            import requests
            import base64
            loop = asyncio.get_event_loop()

            payload = {
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": prompt,
                "width": size[0],
                "height": size[1],
                "steps": 4,
                "response_format": "b64_json",
            }
            headers = {"Authorization": f"Bearer {self.together_api_key}"}

            def _call():
                return requests.post(
                    "https://api.together.xyz/v1/images/generations",
                    json=payload, headers=headers, timeout=30,
                )

            resp = await loop.run_in_executor(None, _call)
            data = resp.json()

            if "data" in data:
                img_b64 = data["data"][0]["b64_json"]
                img_data = base64.b64decode(img_b64)
                buf = BytesIO(img_data)
                buf.seek(0)
                logger.info("[Together] Image generated via Flux API.")
                return buf

        except Exception as exc:
            logger.error("[Together] Studio generation failure: %s", exc)

        return None

    async def _offload_to_dcn_studio(
        self, prompt: str, style: str, size: Tuple[int, int], enhance: bool
    ) -> Optional[BytesIO]:
        """Enqueues image task to specialized DCN Stream and waits for reactive completion."""
        if not HAS_REDIS_ASYNC: return None
        
        mission_id = f"studio_{os.urandom(4).hex()}"
        task_pkg = {
            "mission_id": mission_id,
            "node_id": "studio_task",
            "type": "studio_generate",
            "payload": {
                "prompt": prompt,
                "style": style,
                "width": size[0],
                "height": size[1],
                "enhance": enhance
            },
            "ts": asyncio.get_event_loop().time()
        }
        
        try:
            # 1. Enqueue to specialized studio stream
            # We use a dcn:studio_stream to allow workers to specialize
            await r_async.xadd("dcn:studio_stream", {"payload": json.dumps(task_pkg)}, maxlen=100)
            
            # 2. Wait reactively for result (v2.1 PubSub)
            pubsub = r_async.pubsub()
            channel = f"dcn:mission:{mission_id}:events"
            await pubsub.subscribe(channel)
            
            logger.info(f"⏳ [Studio] Waiting for swarm node to process {mission_id}...")
            
            start = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start) < 60: # 60s timeout for visuals
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    data = json.loads(msg["data"])
                    if data.get("event") == "node_complete":
                        # Fetch result from result key (Base64'd since it's an image)
                        res_key = f"dcn:mission:{mission_id}:result"
                        img_b64 = await r_async.get(res_key)
                        if img_b64:
                            import base64
                            buf = BytesIO(base64.b64decode(img_b64))
                            buf.seek(0)
                            await pubsub.unsubscribe(channel)
                            await pubsub.close()
                            return buf
            
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception as e:
            logger.error(f"[Studio] DCN Error: {e}")
            
        return None

