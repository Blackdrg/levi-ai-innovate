import httpx
import os
import logging
from openai import AsyncOpenAI
from backend.circuit_breaker import circuit_breaker
from backend.api.v8.telemetry import broadcast_mission_event
from backend.utils.metrics import LLM_LATENCY, LLM_ERRORS

logger = logging.getLogger(__name__)

# LEVI-AI v22.0.0-GA: Universal Sovereign LLM Client

@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def call_local_llm(
    prompt: str,
    model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
    system: str = "You are the LEVI-AI Sovereign Orchestrator."
) -> str:
    """
    Sovereign v22: Hardened asynchronous call to the local Ollama API.
    Includes circuit-aware retries and telemetry.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    start_time = asyncio.get_event_loop().time()
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False
                }
            )
            response.raise_for_status()
            
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            LLM_LATENCY.observe(latency)
            
            result = response.json()["response"]
            
            # Telemetry Pulse
            broadcast_mission_event("system", "llm_pulse", {
                "model": model,
                "latency_ms": round(latency, 2),
                "status": "success"
            })
            
            return result
    except Exception as e:
        LLM_ERRORS.inc()
        logger.error(f"[LLM] Critical outage or timeout: {e}")
        broadcast_mission_event("system", "llm_pulse", {"status": "error", "error": str(e)})
        raise

# For OpenAI-compatible drop-in (Graduated for local-first)
local_client = AsyncOpenAI(
    base_url=f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/v1",
    api_key="sovereign-native"
)

import asyncio
