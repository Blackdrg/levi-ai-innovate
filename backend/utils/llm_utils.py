import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

async def _async_call_llm_api(
    messages: List[Dict],
    model: str = "llama3.1:8b",
    provider: str = "ollama",
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> str:
    """
    Sovereign LLM Utility v13.0.
    100% Local Inference via Ollama. Cloud providers decoupled.
    """
    return await call_ollama_llm(messages, model=model, temperature=temperature)

async def call_lightweight_llm(messages: List[Dict], model: Optional[str] = None) -> str:
    """
    Fast-path internal reasoning call.
    Prioritizes Local Ollama (llama3) for low-latency extraction.
    """
    target_model = model or os.getenv("OLLAMA_MODEL_GENERAL", "llama3.1:8b")
    
    if os.getenv("OLLAMA_BASE_URL"):
        return await _async_call_llm_api(
            messages=messages,
            model=target_model,
            provider="ollama",
            temperature=0.3
        )
        
    return await _async_call_llm_api(
        messages=messages,
        model=target_model if target_model else "llama-3.1-8b-instant",
        temperature=0.3
    )

async def call_ollama_llm(
    messages: List[Dict],
    model: str = "llama3.1:8b",
    temperature: float = 0.7
) -> str:
    """
    Communicates with local Ollama daemon.
    """
    import httpx
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature}
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"[Ollama] Local inference failed: {e}")
        return "Local brain offline. Searching for cloud fallback..."
