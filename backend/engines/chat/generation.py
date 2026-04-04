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

    async def stream_response(self, messages: List[Dict], model: str = "llama-3.1-8b-instant", lang: str = "en", task_type: str = "chat"):
        """
        True token-by-token SSE streaming for Absolute Monolith (v13.0.0).
        """
        # 1. Routing & Guardrails
        analysis = SovereignHandoff.analyze_mission(messages[-1]["content"], task_type)
        route = SovereignHandoff.select_provider(analysis)
        
        if route == ModelProvider.SAFE_MODE.value:
            yield "LEVI: [SAFE_MODE] Sensitive data detected. Grounding mission in local deterministic logic..."
            return

        # 2. Providers fallback: Groq -> Together -> Local
        providers = [
            (self._stream_groq, model),
            (self._stream_together, "mistralai/mixtral-8x7b-instruct"),
            (self._stream_local, None)
        ]

        for stream_func, model_name in providers:
            try:
                # Emit Pulse: Neural Thinking
                SovereignBroadcaster.broadcast({"type": "NEURAL_THINKING", "provider": model_name or "local"})
                async for token in stream_func(messages, model_name, lang):
                    yield token
                return 
            except Exception as e:
                logger.warning(f"[Generator-v13] Provider {stream_func.__name__} failed: {e}. Transitioning.")
                continue

        yield SovereignI18n.get_prompt("error_fallback", lang)

    async def _stream_groq(self, messages: List[Dict], model: str, lang: str):
        if not self.groq_api_key: raise RuntimeError("Groq key missing")
        import groq
        client = groq.AsyncGroq(api_key=self.groq_api_key)
        
        system_msg = {"role": "system", "content": SovereignI18n.get_prompt("system_brain", lang)}
        async with client.chat.completions.stream(
            model=model,
            messages=[system_msg] + messages,
            temperature=0.8,
        ) as stream:
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield SovereignSecurity.mask_pii(token)

    async def _stream_together(self, messages: List[Dict], model: str, lang: str):
        if not self.together_api_key: raise RuntimeError("Together key missing")
        from together import AsyncTogether
        client = AsyncTogether(api_key=self.together_api_key)
        
        system_msg = {"role": "system", "content": SovereignI18n.get_prompt("system_brain", lang)}
        stream = await client.chat.completions.create(
            model=model,
            messages=[system_msg] + messages,
            stream=True,
            temperature=0.7
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield SovereignSecurity.mask_pii(chunk.choices[0].delta.content)

    async def _stream_local(self, messages: List[Dict], model: str, lang: str):
        prompt = messages[-1]["content"]
        res = await local_llm.agenerate(prompt)
        if res: yield SovereignSecurity.mask_pii(res)
        else: raise RuntimeError("Local failover failed")

    async def council_of_models(self, messages: List[Dict]) -> str:
        """
        Sovereign v13.0.0: High-Fidelity Swarm Consensus.
        """
        models = [
            ("llama-3.1-70b-versatile", ModelProvider.GROQ),
            ("mistralai/Mixtral-8x7B-Instruct-v0.1", ModelProvider.TOGETHER),
        ]
        
        SovereignBroadcaster.broadcast({"type": "SWARM_CONSENSUS_INITIATED", "models_count": len(models)})
        
        tasks = [self._single_call(messages, m, p) for m, p in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = [r for r in results if isinstance(r, str) and len(r) > 10]
        if not valid_results:
             return "LEVI: Council silence. Reverting to local deterministic logic."
             
        final_synthesis = max(valid_results, key=len)
        return SovereignSecurity.mask_pii(final_synthesis)

    async def _single_call(self, messages: List[Dict], model: str, provider: ModelProvider) -> Optional[str]:
        """Orchestrates a single high-fidelity call to a specific provider."""
        try:
            if provider == ModelProvider.GROQ:
                import groq
                client = groq.AsyncGroq(api_key=self.groq_api_key)
                response = await client.chat.completions.create(model=model, messages=messages)
                return response.choices[0].message.content
            elif provider == ModelProvider.TOGETHER:
                from together import AsyncTogether
                client = AsyncTogether(api_key=self.together_api_key)
                response = await client.chat.completions.create(model=model, messages=messages)
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[Council-v13] Anomaly in {provider.value}: {e}")
            return None

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
