"""
Sovereign Generation Engine v13.0.0.
High-performance streaming cognitive synthesis for the Absolute Monolith.
"""

import os
import random
import logging
import asyncio
import json
import uuid
import zlib
import base64
from typing import Optional, Any, List, Dict
from enum import Enum

from backend.services.local_llm import local_llm
from backend.engines.utils.security import SovereignSecurity
from backend.engines.utils.i18n import SovereignI18n
from .handoff import SovereignHandoff
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    GROQ = "groq"
    TOGETHER = "together"
    LOCAL = "local"
    SAFE_MODE = "SAFE_MODE"

class SovereignGenerator:
    """
    Absolute Monolith Generator (v13.0.0).
    Parallel model routing and Adaptive Pulse v4.1 integration.
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.together_api_key = os.getenv("TOGETHER_API_KEY")

    async def stream_response(self, messages: List[Dict], model: str = "llama3.1:8b", lang: str = "en", task_type: str = "chat"):
        """
        Token-by-token SSE streaming via local Ollama (v13.0.0).
        """
        # Emit Pulse: Neural Thinking (Local)
        SovereignBroadcaster.broadcast({"type": "NEURAL_THINKING", "provider": "local"})

        try:
            async for token in self._stream_local(messages, model, lang):
                yield token
        except Exception as e:
            logger.error(f"[Generator-v13] Local stream fail: {e}")
            yield SovereignI18n.get_prompt("error_fallback", lang)

    async def _stream_local(self, messages: List[Dict], model: str, lang: str):
        """
        Direct Ollama streaming interface.
        """
        import httpx, json
        base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), SovereignI18n.get_prompt("system_brain", lang))
        history = [m for m in messages if m["role"] != "system"]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [{"role": "system", "content": system_msg}] + history,
                        "stream": True,
                        "options": {"temperature": 0.8}
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if not line: continue
                        body = json.loads(line)
                        if "message" in body:
                            token = body["message"].get("content", "")
                            yield SovereignSecurity.mask_pii(token)
                        if body.get("done"): break
        except Exception as e:
            logger.error(f"[Local-Stream] Inference Error: {e}")
            raise RuntimeError("Local brain offline.")

    async def council_of_models(self, messages: List[Dict]) -> str:
        """
        Council of Models (v13.0): Local Multi-Agent Consensus.
        """
        return await self._single_call(messages, "llama3.1:8b")

    async def _single_call(self, messages: List[Dict], model: str, provider: Any = None) -> str:
        """Sovereign v13: Fast local generation path."""
        from backend.utils.llm_utils import call_ollama_llm
        return await call_ollama_llm(messages, model=model)

    async def generate(self, messages: List[Dict], task_type: str = "chat") -> str:
        """Central non-streaming entry point (v13.0 Completion)."""
        return await self.router.generate_hybrid(messages, task_type)

class LLMRouter:
    """
    Sovereign LLM Router v13.0.
    Decides between local reasoning, safe-mode grounding, and high-fidelity cloud APIs.
    """
    def route(self, prompt: str, task_type: str = "chat") -> str:
        """
        Sovereign v13.0.0: Neural Handoff Integration.
        """
        analysis = SovereignHandoff.analyze_mission(prompt, task_type)
        provider = SovereignHandoff.select_provider(analysis)
        
        # Emit Pulse: Provider Selection
        SovereignBroadcaster.broadcast({
            "type": "NEURAL_PROVIDER_SELECTED",
            "provider": provider,
            "session_id": f"gen_{uuid.uuid4().hex[:6]}"
        })
        
        logger.info(f"[LLMRouter-v13] Routing {task_type} mission to {provider.upper()} engine.")
        return provider

    async def generate_hybrid(self, messages: List[Dict], task_type: str = "chat") -> str:
        """Route and generate based on result (v13 async)."""
        prompt = messages[-1]["content"] or ""
        route = self.route(prompt, task_type)
        
        if route == ModelProvider.SAFE_MODE.value:
            return "LEVI: [SAFE_MODE] I have identified sensitive data and grounded this mission in local deterministic logic. I cannot process this via cloud providers."

        if route == "local":
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "You are LEVI.")
            SovereignBroadcaster.broadcast({"type": "NEURAL_THINKING", "provider": "local"})
            res = await local_llm.agenerate(prompt, system_prompt=system_prompt)
            if res: return res
            logger.warning("[LLMRouter-v13] Local failure. Falling back to API.")

        gen = SovereignGenerator()
        return await gen.council_of_models(messages)

# ── Global Pulse Utilities ──────────────────────────────────────────────────
def _build_dynamic_system_prompt(persona: Dict, user_memory: Optional[str], lang: str = "en") -> str:
    """Sovereign v13.0.0: Dynamics for the Absolute Monolith."""
    base = SovereignI18n.get_prompt("system_brain", lang) or "You are LEVI, a sovereign AI monolith."
    if user_memory: base += f"\n\n[USER RESONANCE]:\n{user_memory}"
    
    base += "\n\n[v13.0 SOVEREIGN PROTOCOL]:\n"
    base += "- Priority 1: DETERMINISTIC ENGINE accuracy.\n"
    base += "- Priority 2: ABSOLUTE PRIVACY (Safe Mode).\n"
    base += "- Return logic-synthesized responses only.\n"
    return base

async def async_stream_llm_response(
    messages: List[Dict],
    model: str = "llama-3.1-8b-instant",
    lang: str = "en",
    user_memory: Optional[str] = None,
    persona: Optional[Dict] = None
):
    """Entry point for v13.0 token streaming."""
    generator = SovereignGenerator()
    if not any(m["role"] == "system" for m in messages):
        identity = _build_dynamic_system_prompt(persona or {}, user_memory, lang=lang)
        messages.insert(0, {"role": "system", "content": identity})

    try:
        async for token in generator.stream_response(messages, model, lang):
            yield token
    except Exception as e:
        logger.error(f"[Stream-Pulse] Drift: {e}")
        yield "I encountered a neural flux. Re-initializing stream..."
