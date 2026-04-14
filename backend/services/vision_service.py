import logging
import os
import base64
from typing import List, Optional, Dict, Any
from backend.utils.llm_utils import call_ollama_llm

logger = logging.getLogger(__name__)

class VisionService:
    """
    Sovereign Vision Engine v16.1.
    Bridges Local LLaVA-1.5 for multimodal cognitive perception.
    """
    
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL_VISION", "llava:7b")
        self.enabled = os.getenv("OLLAMA_BASE_URL") is not None

    async def analyze_image(self, image_data: str, prompt: str = "Describe this image in detail.") -> str:
        """
        Analyzes an image using the local LLaVA provider.
        image_data: base64 encoded string or path to image.
        """
        if not self.enabled:
            return "Vision service offline (Ollama missing)."

        # 1. Handle image data (convert path to b64 if needed)
        b64_image = image_data
        if os.path.exists(image_data):
            try:
                with open(image_data, "rb") as f:
                    b64_image = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logger.error(f"[Vision] Failed to read image from path: {e}")
                return "Error reading image file."

        # 2. Prepare Multimodal Payload
        messages = [
            {
                "role": "user",
                "content": prompt,
                "images": [b64_image]
            }
        ]

        # 3. Call Local Provider
        logger.info(f"🚀 [Vision] Analyzing image with {self.model}...")
        description = await call_ollama_llm(messages, model=self.model)
        
        return description

vision_service = VisionService()
