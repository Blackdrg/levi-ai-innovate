import os
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class LocalLLM:
    """
    Sovereign Local Inference Engine v8.
    Wrapper for llama-cpp-python to reduce external API dependency.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalLLM, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.model_path = os.getenv("LOCAL_MODEL_PATH", "models/llama-3.gguf")
            cls._instance._initialize_model()
        return cls._instance

    def is_available(self) -> bool:
        """v13.0 Model Integrity Probe."""
        return self.model is not None

    def _initialize_model(self):
        """Lazy load the GGUF model."""
        if not os.path.exists(self.model_path):
            logger.warning(f"[LocalLLM] Model file not found at {self.model_path}. Local inference will be unavailable.")
            return

        try:
            from llama_cpp import Llama
            logger.info(f"[LocalLLM] Loading model: {self.model_path}")
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=4096,
                n_threads=os.cpu_count() or 4,
                verbose=False
            )
            logger.info("[LocalLLM] Model loaded successfully.")
        except Exception as e:
            logger.error(f"[LocalLLM] Failed to load local model: {e}")

    async def agenerate(self, prompt: str, system_prompt: str = "You are LEVI, a local AI.", max_tokens: int = 512) -> Optional[str]:
        """Async local generation for v13.0.0 brain stream."""
        if not self.model:
            return None
            
        try:
            # We use to_thread to prevent blocking the async loop by llama-cpp
            import asyncio
            return await asyncio.to_thread(self.generate, prompt, system_prompt, max_tokens)
        except Exception as e:
            logger.error(f"[LocalLLM] Async generation error: {e}")
            return None

    def generate(self, prompt: str, system_prompt: str = "You are LEVI, a local AI.", max_tokens: int = 512) -> Optional[str]:
        """Synchronous local generation."""
        if not self.model:
            return None

        try:
            formatted_prompt = f"System: {system_prompt}\nUser: {prompt}\nAI:"
            output = self.model(
                formatted_prompt,
                max_tokens=max_tokens,
                stop=["User:", "System:"],
                echo=False
            )
            return output["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"[LocalLLM] Local generation error: {e}")
            return None

# Global instance
local_llm = LocalLLM()
