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
            
            # v9.8.1 Sovereign Shield: Mandatory PII Scrubbing for Cloud
            try:
                from .llm_guard import LLMGuard
                scrubbed_prompt = LLMGuard.secure_outbound(prompt)
                if scrubbed_prompt != prompt:
                    logger.info("[NeuralHandoff] Sovereign Shield: PII Masked in outbound prompt.")
                    context["pii_masked"] = True
            except Exception as e:
                logger.error(f"[NeuralHandoff] Security Layer failure: {e}. Aborting cloud route.")
                return await self._call_local(prompt, context)
                
            logger.info(f"[NeuralHandoff] Routing to CLOUD ({self.cloud_provider}). Reason: Complexity={complexity}")
            return {"target": "cloud", "provider": self.cloud_provider, "prompt": scrubbed_prompt}

    async def _call_local(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        LeviBrain v9.8: Direct Local Inference Execution.
        Orchestrates calls to local LLM servers with zero external telemetry.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if self.local_provider == "ollama":
                    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
                    logger.debug(f"[NeuralHandoff] Dispatching to Ollama ({model})...")
                    
                    response = await client.post(
                        self.ollama_url,
                        json={
                            "model": model,
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
                            "model": model,
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
