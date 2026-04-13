import os
import logging
import json
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# v15.0 GA: CONFIDENCE THRESHOLD FOR CLOUD FALLBACK
LLM_CONFIDENCE_THRESHOLD = 0.65

async def _async_call_llm_api(
    messages: List[Dict[str, Any]],
    model: str = "llama3.1:8b",
    temperature: float = 0.7,
    use_heavyweight: bool = False
) -> str:
    """
    Sovereign LLM Stack v15.0: KILL EXTERNAL DEPENDENCY.
    Prioritizes local inference (Ollama/vLLM) to reach 75% internal AI goal.
    """
    local_model = model
    if use_heavyweight:
        local_model = os.getenv("OLLAMA_MODEL_HEAVY", "llama3.1:70b")
    
    # 1. PRIMARY: LOCAL INFERENCE (Ollama)
    local_res = await call_ollama_llm(messages, model=local_model, temperature=temperature)
    
    # 2. HYBRID FALLBACK: CHECK CONFIDENCE / AVAILABILITY
    if "Local brain offline" in local_res or len(local_res) < 10:
        logger.warning(f"[LLM] Local brain weak or offline. Assessing cloud fallback...")
        return await call_cloud_fallback(messages, temperature=temperature)
    
    return local_res

async def call_lightweight_llm(messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
    """Step 3.2: Replaces OpenAI calls in Planner/Reasoning with Local inference."""
    return await _async_call_llm_api(
        messages=messages,
        model=model or os.getenv("OLLAMA_MODEL_GENERAL", "llama3.1:8b"),
        temperature=0.3
    )

async def call_heavyweight_llm(messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
    """Used for deep reasoning missions."""
    return await _async_call_llm_api(
        messages=messages,
        model=model or os.getenv("OLLAMA_MODEL_HEAVY", "llama3.1:70b"),
        temperature=0.7,
        use_heavyweight=True
    )

async def call_ollama_llm(
    messages: List[Dict[str, Any]],
    model: str = "llama3.1:8b",
    temperature: float = 0.7
) -> str:
    import httpx
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
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
        return "Local brain offline."

async def call_cloud_fallback(messages: List[Dict[str, Any]], temperature: float = 0.7) -> str:
    """
    Step 3.4: Hybrid Mode Fallback.
    Only called if local inference fails or confidence is too low.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Critical: Local & Cloud brains offline."

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        logger.info("🚀 [Hybrid] Local weak. Escaping to Cloud (GPT-4o)...")
        response = await client.chat.completions.create(
            model="gpt-4o", 
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"[Fallback] Cloud failed: {e}")
        return "Cognitive blackout: All LLM providers failed."
