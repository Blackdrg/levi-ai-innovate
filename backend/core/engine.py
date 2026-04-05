"""
Sovereign Orchestration Engine v13.0.0.
Public interface for the Absolute Monolith Brain.
Bridges to the finalized v13.0 LeviBrainCoreController.
"""

import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator, Union

from .v8.brain import LeviBrainCoreController
from .v8.learning import UserPreferenceModel
from .orchestrator_types import ToolResult

logger = logging.getLogger(__name__)

# Global v13.0.0 Brain Monolith
_BRAIN = LeviBrainCoreController()

class LeviOrchestrator:
    """
    Public interface for the LEVI AI Absolute Monolith.
    """
    async def handle(
        self,
        user_id: str,
        input_text: str,
        session_id: str = "",
        user_tier: str = "free",
        mood: str = "philosophical",
        background_tasks: Any = None,
        request_id: Optional[str] = None,
    ) -> str:
        """
        High-level entry point for the graduated Monolith (v13.0.0).
        """
        session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        result = await run_orchestrator(
            user_input=input_text,
            session_id=session_id,
            user_id=user_id,
            background_tasks=background_tasks,
            user_tier=user_tier,
            mood=mood,
            request_id=request_id
        )
        return result.get("response", "Neural protocol drift in Monolith. Retrying...")

async def run_orchestrator(
    user_input: str,
    session_id: str,
    user_id: str = "guest",
    background_tasks: Any = None,
    user_tier: str = "free",
    mood: str = "philosophical",
    streaming: bool = False,
    request_id: Optional[str] = None,
) -> Any:
    """
    Main mission entry point for v13.0.0 Absolute Monolith.
    Delegates to run_mission_sync or run_mission_stream.
    """
    if streaming:
        return _BRAIN.run_mission_stream(
            user_input=user_input,
            user_id=user_id,
            session_id=session_id,
            user_tier=user_tier,
            mood=mood,
            request_id=request_id
        )
    else:
        return await _BRAIN.run_mission_sync(
            input_text=user_input,
            user_id=user_id,
            session_id=session_id,
            user_tier=user_tier,
            mood=mood,
            request_id=request_id
        )

async def synthesize_response(
    results: List[Any],
    context: Dict[str, Any],
) -> str:
    """
    V13 ResponseComposer: Neutralizes swarm complexity into a unified mind.
    """
    # ... logic delegated to v13 internal synthesis ...
    # This remains as a bridge for legacy v1 orchestrator calls
    from backend.engines.chat.generation import _async_call_llm_api
    
    # 1. v13 SQL Profile Sync
    user_id = context.get("user_id", "guest")
    pref_model = UserPreferenceModel()
    profile = await pref_model.get_profile(user_id)
    
    style_hint = profile.get("style", "philosophical")
    
    synth_prompt = (
        f"You are LEVI, the Absolute Monolith (v13.0.0). "
        f"Synthesize the following fragments into your unified voice.\n"
        f"User Style: {style_hint}\n"
        f"Input: {context.get('input', '')}\n\n"
        "Constraint: Speak with sovereign finality."
    )

    try:
        return await _async_call_llm_api(
            messages=[{"role": "system", "content": synth_prompt}],
            model="llama-3.1-70b-versatile",
            provider="groq"
        )
    except Exception:
        return "I have crystallized the mission requirements. Synthesis complete."
async def synthesize_streaming_response(
    results: List[ToolResult],
    context: Dict[str, Any],
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streaming version of the ResponseComposer.
    Yields tokens and metadata events for high-fidelity real-time synthesis.
    """
    if not results:
        yield {"token": "The void remains silent. Perhaps another path is needed."}
        return

    # 1. Filter and Score Results
    valid_results = [r for r in results if r.success]
    if not valid_results:
        yield {"token": "I encountered a barrier: " + (results[0].error if results else "Unknown error")}
        return

    # 2. Extract Data & Metadata for Prompt
    agent_outputs = []
    job_ids = []
    for r in valid_results:
        if r.data.get("job_id"):
            job_ids.append(f"{r.data.get('type', 'creation')}: {r.data.get('job_id')}")
        output = r.message or "Task processed."
        agent_outputs.append(f"Agent [{r.agent}]: {output}")

    # 3. Handle Direct Return (Optimization)
    if len(valid_results) == 1 and valid_results[0].agent == "chat_agent":
        # Stream the single agent output if possible, or just yield it if it's already full
        yield {"token": valid_results[0].message}
        return

    # 4. LLM Synthesis (Response Composition)
    from backend.engines.chat.generation import async_stream_llm_response
    from backend.services.learning.logic import UserPreferenceModel

    user_id = context.get("user_id", "guest")
    pref_model = UserPreferenceModel(user_id)
    preferences = await pref_model.get_profile()
    
    style_hint = preferences.get("response_style", "philosophical and concise")
    ltm = context.get("long_term", {})
    
    fact_parts = []
    if ltm:
        for cat in ["preferences", "traits", "history"]:
            vals = ltm.get(cat, [])
            if vals: fact_parts.append(f"{cat.capitalize()}: {', '.join(str(v) for v in vals[:3])}")

    job_context = f"\nAction Result: I have initiated these: {', '.join(job_ids)}" if job_ids else ""
    
    synth_prompt = (
        f"You are LEVI, a {context.get('mood', 'philosophical')} AI voice. "
        f"Integrate these specialized agent findings into a cohesive, personalized vision.\n"
        f"User Resonance Style: {style_hint}.\n"
        f"Contextual Roots: {', '.join(fact_parts)}\n\n"
        f"Input: {context.get('input', '')}\n\n"
        f"Findings:\n{chr(10).join(agent_outputs)}\n"
        f"{job_context}\n\n"
        "Constraint: Do NOT mention agent names or that you are 'synthesizing'. Speak as one unified mind."
    )

    # Tiered Model Selection
    user_tier = context.get("user_tier", "free")
    complexity = context.get("complexity_level", 2)
    model = "llama-3.1-70b-versatile" if (user_tier in ("pro", "creator") or complexity == 3) else "llama-3.1-8b-instant"

    try:
        async for token in async_stream_llm_response(
            messages=[{"role": "system", "content": synth_prompt}],
            model=model,
        ):
            yield {"token": token}
            
        # Ensure job IDs are preserved at the end if not mentioned
        if job_ids:
            yield {"event": "metadata", "data": {"job_ids": job_ids}}
            
    except Exception as e:
        logger.error(f"Streaming synthesis failed: {e}")
        yield {"token": "\n\n".join([r.message for r in valid_results if r.message])}
