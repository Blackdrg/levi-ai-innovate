import httpx
from openai import AsyncOpenAI
import os

# base_llm.py — drop this in as your universal LLM client

async def call_local_llm(
    prompt: str,
    model: str = "llama3.1:8b",
    system: str = "You are a helpful assistant."
) -> str:
    """
    Direct asynchronous call to the local Ollama API.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
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
        return response.json()["response"]

# For OpenAI-compatible drop-in (works with LangChain, etc.)
local_client = AsyncOpenAI(
    base_url=f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/v1",
    api_key="ollama"  # dummy key, not used
)
