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
    Sovereign LLM Utility v14.1.0-Stability.
    Hybrid routing: Prioritizes local inference with cloud fallback.
    """
    try:
        if provider == "ollama":
            res = await call_ollama_llm(messages, model=model, temperature=temperature)
            if "Local brain offline" in res:
                 return await call_cloud_fallback(messages, temperature=temperature)
            return res
        return await call_cloud_fallback(messages, temperature=temperature)
    except Exception as e:
        logger.error(f"[LLM Router] Failed to route request: {e}")
        return await call_cloud_fallback(messages, temperature=temperature)

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

async def call_cloud_fallback(messages: List[Dict], temperature: float = 0.7) -> str:
    """
    Refined Fallback Routing: OpenAI (Reliability) -> Groq (Speed).
    """
    # 1. Primary Fallback: OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
            logger.info("🚀 [Fallback] Routing to OpenAI (GPT-4o-mini)...")
            response = await client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL_FALLBACK", "gpt-4o-mini"),
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[Fallback] OpenAI failed: {e}")

    # 2. Secondary Fallback: Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=groq_key)
            logger.info("🚀 [Fallback] Routing to Groq (Llama-3-70b)...")
            response = await client.chat.completions.create(
                model=os.getenv("GROQ_MODEL_FALLBACK", "llama3-70b-8192"),
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[Fallback] Groq failed: {e}")

    return "All LLMs offline. System restricted to deterministic logic."
