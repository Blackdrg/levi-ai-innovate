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
from .orchestrator_types import ToolResult

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
    results: List[ToolResult],
    context: Dict[str, Any],
) -> str:
    """
    The ResponseComposer: Synthesizes multiple agent outputs into LEVI's unified voice.
    Handles conflict resolution, confidence-based filtering, and job integration.
    """
    if not results:
        return "The void remains silent. Perhaps another path is needed."

    # 1. Filter and Score Results
    valid_results = [r for r in results if r.success]
    if not valid_results:
        # Fallback to the error message of the first failed critical tool
        for r in results:
            if r.error: return f"I encountered a barrier: {r.error}"
        return "I could not complete the requested reasoning chain."

    # 2. Extract Data & Metadata
    agent_outputs = []
    job_ids = []
    total_cost = 0
    max_confidence = 0.0

    for r in valid_results:
        total_cost += r.cost_score
        max_confidence = max(max_confidence, getattr(r, 'confidence', 0.8))
        
        # Capture creation identifiers
        if r.data.get("job_id"):
            job_ids.append(f"{r.data.get('type', 'creation')}: {r.data.get('job_id')}")

        output = r.message or "Task processed."
        agent_outputs.append(f"Agent [{r.agent}]: {output}")

    # 3. Direct Return Optimization (Level 1/2 with single high-confidence agent)
    if len(valid_results) == 1 and valid_results[0].agent == "chat_agent":
        return valid_results[0].message

    # 4. LLM Synthesis (Response Composition)
    from backend.engines.chat.generation import _async_call_llm_api
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
        synth_response = await _async_call_llm_api(
            messages=[{"role": "system", "content": synth_prompt}],
            model=model,
            provider="groq",
            temperature=0.7
        )
        
        # Ensure job IDs are preserved if missing from LLM output
        if job_ids and not any(jid in synth_response for jid in job_ids):
             return f"{synth_response}\n\nCreation Tracking: {', '.join(job_ids)}"
        
        return synth_response
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        # Fallback: simple merge of outputs
        return "\n\n".join([r.message for r in valid_results if r.message])
