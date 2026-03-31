"""
backend/services/orchestrator/engine.py

LEVI AI Orchestrator Utilities.
Contains synthesis logic and the public class interface.
Core routing is delegated to .brain.LeviBrain.
"""

import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List

from .brain import LeviBrain

logger = logging.getLogger(__name__)

# Global LeviBrain Instance
_BRAIN = LeviBrain()

class LeviOrchestrator:
    """
    Public interface for the LEVI AI Brain.
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
        High-level entry point returning only the response string.
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
        return result.get("response", "I encountered a minor paradox. Please try again.")

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
    Main entry point for all LEVI AI requests.
    Delegates to the unified deterministic pipeline in LeviBrain.
    """
    return await _BRAIN.route(
        user_input=user_input,
        user_id=user_id,
        session_id=session_id,
        user_tier=user_tier,
        mood=mood,
        background_tasks=background_tasks,
        streaming=streaming,
        request_id=request_id
    )

async def synthesize_response(
    results: List[Any],
    context: Dict[str, Any],
) -> str:
    """
    Synthesize multiple agent outputs into LEVI's unified philosophical voice.
    """
    if not results:
        return "The void remains silent. Please try another query."

    # If only one result and it's successful chat_agent, return it directly
    if len(results) == 1:
        r = results[0]
        # Handle both ToolResult objects and legacy dicts
        msg = r.message if hasattr(r, 'message') else r.get("message")
        success = r.success if hasattr(r, 'success') else r.get("success", True)
        agent = r.agent if hasattr(r, 'agent') else r.get("agent")
        
        if success and agent == "chat_agent" and msg:
            return msg

    from backend.generation import _async_call_llm_api
    from backend.learning import UserPreferenceModel

    user_id = context.get("user_id", "guest")
    pref_model = UserPreferenceModel(user_id)
    preferences = await pref_model.get_profile()

    ltm = context.get("long_term", {})
    pulse = context.get("interaction_pulse", "stable")

    fact_parts = []
    if ltm:
        for cat in ["preferences", "traits", "history"]:
            vals = ltm.get(cat, [])
            if vals:
                fact_parts.append(f"{cat.capitalize()}: {', '.join(vals[:5])}")

    agent_outputs = []
    for r in results:
        msg = r.message if hasattr(r, 'message') else r.get("message")
        err = r.error if hasattr(r, 'error') else r.get("error")
        agent = r.agent if hasattr(r, 'agent') else r.get("agent")
        
        output = msg or err or "Task completed with no output."
        agent_outputs.append(f"Agent [{agent}]: {output}")

    # Phase 7 & 8: Contextual Integration
    style_hint = preferences.get("response_style", "philosophical and concise")
    topics_hint = ", ".join(preferences.get("top_topics", []))

    # Detect background jobs
    job_ids = []
    agent_outputs = []
    for r in results:
        msg = r.message if hasattr(r, 'message') else r.get("message", "")
        err = r.error if hasattr(r, 'error') else r.get("error")
        agent = r.agent if hasattr(r, 'agent') else r.get("agent", "unknown")
        data = r.data if hasattr(r, 'data') else r.get("data", {})
        
        # Capture job IDs for synthesis
        if data.get("job_id"):
            job_ids.append(f"{data.get('type', 'job')}: {data.get('job_id')}")

        output = msg or err or "Task completed."
        agent_outputs.append(f"Agent [{agent}]: {output}")

    job_context = f"\nAction Result: I have initiated these creations: {', '.join(job_ids)}" if job_ids else ""

    synth_prompt = (
        f"Role: You are LEVI, a {context.get('mood', 'philosophical')} AI voice. "
        f"Goal: Synthesize agent outputs into a cohesive, personalized response. "
        f"User Style Preference: {style_hint}. Interest context: {topics_hint}.\n"
        "Voice: Poetic, direct, and observant. Do NOT mention agent names or 'results'.\n"
        f"Context:\n{chr(10).join(fact_parts)}\n\n"
        f"Task: {context.get('input', '')}\n\n"
        f"Agent Data:\n{'---'.join(agent_outputs)}"
        f"{job_context}"
    )

    try:
        synth_response = await _async_call_llm_api(
            messages=[{"role": "system", "content": synth_prompt}],
            model="llama-3.1-70b-versatile" if context.get("user_tier") != "free" else "llama-3.1-8b-instant",
            provider="groq",
            temperature=0.75
        )
        # Ensure job IDs are mentioned if we generated some
        if job_ids and not any(jid in synth_response for jid in job_ids):
             return f"{synth_response}\n\nTracking: {', '.join(job_ids)}"
        return synth_response
    except Exception:
        # Fallback to last valid message
        for r in reversed(results):
            msg = r.message if hasattr(r, 'message') else r.get("message")
            if msg: return msg
        return "Synthesis failed. Let's try another topic."
