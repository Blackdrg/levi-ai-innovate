import os
import logging
import asyncio
from typing import Dict, List, Any, Optional

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

async def call_lightweight_llm(messages: List[Dict]) -> str:
    """
    Fast-path internal reasoning call.
    Prioritizes Local Ollama (llama3) for low-latency extraction.
    """
    # Attempt local first if configured
    if os.getenv("OLLAMA_BASE_URL"):
        return await _async_call_llm_api(
            messages=messages,
            model=os.getenv("OLLAMA_MODEL_GENERAL", "llama3.1:8b"),
            provider="ollama",
            temperature=0.3
        )
        
    return await _async_call_llm_api(
        messages=messages,
        model="llama-3.1-8b-instant",
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
