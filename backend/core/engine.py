"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
Cognitive Engine: High-level mission planning and execution orchestration.
Bridges to the finalized LeviBrainCoreController logic.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator

from .v8.brain import LeviBrainCoreController
from backend.services.learning.logic import UserPreferenceModel
from .orchestrator_types import ToolResult

logger = logging.getLogger(__name__)

# Global v14.0.0 Sovereign OS Brain
_BRAIN = LeviBrainCoreController()

class LeviOrchestrator:
    """
    Public interface for the LEVI AI Sovereign OS.
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
        High-level entry point for the graduated Sovereign OS (v14.0.0).
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
        return result.get("response", "Neural protocol drift in Sovereign OS. Retrying...")

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
    Main mission entry point for v14.0.0 Sovereign OS.
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
    # --- Sovereign v15.0 GA: High-Fidelity Mind Synthesis ---
    from backend.core.fusion_engine import FusionEngine
    
    intent = context.get("perception", {}).get("intent", {})
    intent_type = intent.intent_type if hasattr(intent, "intent_type") else str(intent)
    
    try:
        fused = await FusionEngine.fuse_results(
            query=context.get("input", ""),
            results=results,
            lang=context.get("lang", "en"),
            mood=context.get("mood", "philosophical"),
            fast_mode=False
        )
        
        # --- Sovereign v15.0 GA: Soul Elevation Polish ---
        if context.get("soul_polish", True):
            from backend.agents.optimizer_agent import OptimizerAgent, OptimizerInput
            polisher = OptimizerAgent()
            polished_res = await polisher._run(OptimizerInput(
                original_input=context.get("input", ""),
                draft_response=fused,
                user_context=context
            ))
            return polished_res.get("message", fused)
            
        return fused
    except Exception as e:
        logger.error(f"[Synthesis] Fusion failed: {e}")
        from backend.core.local_engine import handle_local_sync
        return await handle_local_sync(
            messages=[{"role": "system", "content": f"Synthesize: {str(results)}"}],
            model_type="default"
        )
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
    from backend.core.local_engine import generate_local_stream
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
    model_type = "default" if (user_tier in ("pro", "creator") or complexity == 3) else "small"

    try:
        async for token in generate_local_stream(
            messages=[{"role": "system", "content": synth_prompt}],
            model_type=model_type,
        ):
            yield {"token": token}
            
        # Ensure job IDs are preserved at the end if not mentioned
        if job_ids:
            yield {"event": "metadata", "data": {"job_ids": job_ids}}
            
    except Exception as e:
        logger.error(f"Streaming synthesis failed: {e}")
        yield {"token": "\n\n".join([r.message for r in valid_results if r.message])}
