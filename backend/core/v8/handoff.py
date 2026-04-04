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

    async def route_inference(self, prompt: str, context: Dict[str, Any], task_type: str = "general") -> Dict[str, Any]:
        """
        LeviBrain v12.0 Neural Router.
        Routes based on:
        - Complexity (from context)
        - task_type (intent, reasoning, speed)
        - Latency thresholds & Health
        """
        # Phase 9: Local Sovereignty (Zero-Bandwidth Failover)
        if os.getenv("OFFLINE_MODE") == "true":
             logger.info("[Sovereign] OFFLINE_MODE Active. Forcing Local Inference (Llama 3).")
             return await self._call_local(prompt, context, model="llama3:8b")

        complexity = context.get("complexity", 0.5)
        
        # Phase 5: Health & Latency check
        is_local_healthy = await self.verify_local_health()
        
        # v12.0 Routing Logic:
        # A. Intent Detection -> Phi-3 Mini (Ultra Fast)
        if task_type == "intent" and is_local_healthy:
            logger.info("[NeuralRouter] Routing INTENT to local Phi-3 Mini.")
            return await self._call_local(prompt, context, model="phi3:mini")
            
        # B. Low Complexity -> Mistral 7B (Speed)
        if complexity < 0.4 and is_local_healthy:
             logger.info("[NeuralRouter] Routing simple task to local Mistral 7B.")
             return await self._call_local(prompt, context, model="mistral:7b")

        # C. Moderate Complexity -> Llama 3 8B (Sovereign Reasoning)
        if complexity < 0.7 and is_local_healthy:
             logger.info("[NeuralRouter] Routing reasoned task to local Llama 3 8B.")
             return await self._call_local(prompt, context, model="llama3:8b")

        # D. High Complexity / Local Unhealthy -> Cloud (Groq/OpenAI)
        if not groq_breaker.allow_request():
            logger.warning("[NeuralRouter] CLOUD CIRCUIT OPEN. Forcing local fallback (Llama 3).")
            return await self._call_local(prompt, context, model="llama3:8b")
            
        # Sovereign Shield: PII Scrubbing for Cloud
        try:
            from .llm_guard import LLMGuard
            scrubbed_prompt = LLMGuard.secure_outbound(prompt)
        except:
            scrubbed_prompt = prompt
            
        logger.info(f"[NeuralRouter] Routing complex task to CLOUD ({self.cloud_provider}).")
        return {"target": "cloud", "provider": self.cloud_provider, "prompt": scrubbed_prompt}

    async def _call_local(self, prompt: str, context: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
        """
        LeviBrain v12.0: Targeted Local Inference.
        Supports model-specific routing within Ollama/llama.cpp.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if self.local_provider == "ollama":
                    target_model = model or os.getenv("OLLAMA_MODEL", "llama3:8b")
                    logger.debug(f"[NeuralHandoff] Dispatching to Ollama ({target_model})...")
                    
                    response = await client.post(
                        self.ollama_url,
                        json={
                            "model": target_model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": 0.5, "num_predict": 1024}
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "target": "local",
                            "provider": "ollama",
                            "model": target_model,
                            "response": data.get("response", ""),
                            "success": True
                        }
                    else:
                        logger.warning(f"[NeuralHandoff] Ollama server error ({response.status_code}).")
                        
                elif self.local_provider == "llama.cpp":
                    logger.debug(f"[NeuralHandoff] Dispatching to llama.cpp server...")
                    
                    response = await client.post(
                        self.llama_cpp_url,
                        json={
                            "prompt": prompt,
                            "n_predict": 512,
                            "temperature": 0.3,
                            "stop": ["</s>", "User:", "Assistant:"]
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "target": "local",
                            "provider": "llama.cpp",
                            "response": data.get("content", ""),
                            "success": True
                        }
            
            # If we reach here, local failed or provider was unknown
            logger.error(f"[NeuralHandoff] Local provider ({self.local_provider}) is offline or unreachable.")
            return {"target": "cloud", "fallback": True, "error": "local_unreachable"}
            
        except Exception as e:
            logger.error(f"[NeuralHandoff] Local inference logic breach: {e}")
            return {"target": "cloud", "fallback": True, "error": str(e)}

    async def verify_local_health(self) -> bool:
        """Sovereign Health Check: Verifies if the local inference server is responsive."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                if self.local_provider == "ollama":
                    # Check Ollama version endpoint
                    resp = await client.get(self.ollama_url.replace("/api/generate", "/api/version"))
                    return resp.status_code == 200
                elif self.local_provider == "llama.cpp":
                    # Check llama.cpp props/health
                    resp = await client.get(self.llama_cpp_url.replace("/completion", "/props"))
                    return resp.status_code == 200
            return False
        except:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns the v9.8 Sovereign Status of the inference hierarchy."""
        return {
            "v9.8_sovereign_active": True,
            "local": {
                "active_provider": self.local_provider,
                "endpoints": {
                    "llama_cpp": self.llama_cpp_url,
                    "ollama": self.ollama_url
                }
            },
            "cloud": {
                "primary": self.cloud_provider,
                "circuit_status": "CLOSED" if groq_breaker.allow_request() else "OPEN"
            }
        }
