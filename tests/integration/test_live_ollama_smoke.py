from __future__ import annotations

import os

import httpx
import pytest

from backend.engines.chat.generation import SovereignGenerator
from backend.utils.llm_utils import call_ollama_llm


def _live_ollama_enabled() -> bool:
    return os.getenv("RUN_LIVE_OLLAMA_TESTS", "0") == "1"


async def _probe_ollama() -> bool:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
        return True
    except Exception:
        return False


@pytest.mark.asyncio
async def test_call_ollama_llm_returns_real_response():
    if not _live_ollama_enabled() or not await _probe_ollama():
        pytest.skip("Live Ollama integration not enabled or Ollama is unreachable.")

    response = await call_ollama_llm(
        [
            {"role": "system", "content": "Reply with the single word READY."},
            {"role": "user", "content": "Confirm availability."},
        ]
    )

    assert isinstance(response, str)
    assert response.strip()
    assert "mock" not in response.lower()


@pytest.mark.asyncio
async def test_generator_council_of_models_uses_live_ollama():
    if not _live_ollama_enabled() or not await _probe_ollama():
        pytest.skip("Live Ollama integration not enabled or Ollama is unreachable.")

    generator = SovereignGenerator()
    response = await generator.council_of_models(
        [
            {"role": "system", "content": "Reply with the exact phrase: LIVE OLLAMA OK"},
            {"role": "user", "content": "State the phrase now."},
        ],
        model_tier="L2",
    )

    assert isinstance(response, str)
    assert response.strip()
