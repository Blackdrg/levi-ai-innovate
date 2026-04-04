import os
import logging
import httpx
from typing import Dict, Any, Optional, List
from backend.circuit_breaker import groq_breaker

logger = logging.getLogger(__name__)

class NeuralHandoffManager:
    """
    LeviBrain v9.5: Neural Handoff Manager.
    Intelligently routes inference between Local (llama.cpp/Ollama) and Cloud (Groq/OpenAI/Claude).
    """

    def __init__(self):
        # Local Endpoints (Placeholders)
        self.llama_cpp_url = os.getenv("LLAMA_CPP_URL", "http://localhost:8080/completion")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        
        # Preferred Local Provider: 'llama.cpp' or 'ollama'
        self.local_provider = os.getenv("LOCAL_INFERENCE_PROVIDER", "ollama")
        
        # Cloud Configuration
        self.cloud_provider = os.getenv("CLOUD_INFERENCE_PROVIDER", "groq")

    async def route_inference(self, prompt: str, context: Dict[str, Any], sensitivity: float = 0.5) -> Dict[str, Any]:
        """
        Decides whether to use Local or Cloud inference based on:
        - Complexity (from context)
        - Privacy/Sensitivity
        - Availability
        """
        complexity = context.get("complexity", 0.5)
        is_private = sensitivity > 0.8
        
        # v9.5 Decision Logic:
        # High Sensitivity OR Low Complexity -> LOCAL
        # High Complexity AND Low Sensitivity -> CLOUD
        
        if is_private or complexity < 0.3:
            logger.info(f"[NeuralHandoff] Routing to LOCAL ({self.local_provider}). Reason: Private={is_private}, Complexity={complexity}")
            return await self._call_local(prompt, context)
        else:
            # v9.8 Hardening: Check Cloud Circuit Breaker
            if not groq_breaker.allow_request():
                logger.warning(f"[NeuralHandoff] CLOUD CIRCUIT OPEN. Falling back to LOCAL ({self.local_provider}).")
                return await self._call_local(prompt, context)
                
            logger.info(f"[NeuralHandoff] Routing to CLOUD ({self.cloud_provider}). Reason: Complexity={complexity}")
            return {"target": "cloud", "provider": self.cloud_provider}

    async def _call_local(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for Local Inference execution."""
        try:
            if self.local_provider == "ollama":
                # Ollama Placeholder logic
                return {
                    "target": "local",
                    "provider": "ollama",
                    "url": self.ollama_url,
                    "model": os.getenv("OLLAMA_MODEL", "llama3")
                }
            else:
                # llama.cpp Placeholder logic
                return {
                    "target": "local",
                    "provider": "llama.cpp",
                    "url": self.llama_cpp_url
                }
        except Exception as e:
            logger.error(f"[NeuralHandoff] Local inference routing failed: {e}")
            return {"target": "cloud", "fallback": True}

    def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the inference hierarchy."""
        return {
            "local": {
                "active_provider": self.local_provider,
                "endpoints": {
                    "llama_cpp": self.llama_cpp_url,
                    "ollama": self.ollama_url
                }
            },
            "cloud": {
                "primary": self.cloud_provider
            }
        }
