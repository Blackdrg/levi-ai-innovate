import os
import logging
import asyncio
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

async def _async_call_llm_api(
    messages: List[Dict],
    model: str = "llama-3.1-70b-versatile",
    provider: str = "groq",
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> str:
    """
    Sovereign LLM Utility v8.12.
    Low-level interface for unified cloud inference.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("[LLM-Utils] GROQ_API_KEY is not defined in the environment.")
        return "I am currently disconnected from the neural cloud. Verify system configuration."

    try:
        import groq
        client = groq.AsyncGroq(api_key=api_key)
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"[LLM-Utils] Neural call error: {e}")
        return "I encountered a drift in the communication stream. Please retry the mission."

async def call_lightweight_llm(messages: List[Dict]) -> str:
    """
    Fast-path internal reasoning call.
    Uses Llama 3.1 8B for high-speed deterministic extraction.
    """
    return await _async_call_llm_api(
        messages=messages,
        model="llama-3.1-8b-instant",
        temperature=0.3
    )
