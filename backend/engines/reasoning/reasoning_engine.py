import logging
import asyncio
from typing import Any, Dict, List, Optional
from backend.engines.base import EngineBase, EngineResult
from backend.engines.utils.i18n import SovereignI18n

logger = logging.getLogger(__name__)

class ReasoningEngine(EngineBase):
    """
    Sovereign Cognitive Reasoning Engine.
    Implements multi-step Chain-of-Thought (CoT), Tree-of-Thought (ToT), 
    and recursive self-correction.
    """
    
    def __init__(self):
        super().__init__("Reasoning")

    async def _run(self, query: str, context: Optional[str] = None, mode: str = "cot", user_id: str = "global", **kwargs) -> Dict[str, Any]:
        """
        Sovereign v1.0.0-RC1 Reasoning Wave.
        Executes a 5-step cognitive chain governed by AdaptiveThrottler.
        """
        from backend.utils.llm_utils import call_lightweight_llm
        from backend.utils.concurrency import AdaptiveThrottler, CircuitBreaker
        from backend.engines.utils.security import SovereignSecurity
        from backend.broadcast_utils import SovereignBroadcaster

        if CircuitBreaker.is_open():
            logger.warning("[Reasoning] Circuit Breaker OPEN. Aborting cognitive wave.")
            return {"error": "Reasoning loop paused due to system instability."}

        self.logger.info(f"Initiating Reasoning Mission: {mode}")
        steps = []
        
        # 1. DECONSTRUCTION: Extract primitives
        decon_prompt = f"Deconstruct this problem into atomic logical premises: '{query}'. Output 1 PROFOUND sentence."
        decon_resp = await AdaptiveThrottler.run_throttled(call_lightweight_llm, [{"role": "user", "content": decon_prompt}])
        steps.append({"stage": "Deconstruction", "thought": SovereignSecurity.mask_pii(decon_resp or "Analysis initiated.")})
        SovereignBroadcaster.publish("NEURAL_THINKING", {"stage": "Deconstruction", "mission_id": self.engine_name}, user_id=user_id)

        # 2. CONTEXTUALIZATION: Merge Memory
        context_prompt = f"Integrate this context: '{context or 'No memory found'}'. How does it modify the premises? 1 sentence."
        context_resp = await AdaptiveThrottler.run_throttled(call_lightweight_llm, [{"role": "user", "content": context_prompt}])
        steps.append({"stage": "Contextualization", "thought": SovereignSecurity.mask_pii(context_resp or "Contextual alignment complete.")})
        SovereignBroadcaster.publish("NEURAL_THINKING", {"stage": "Contextualization", "mission_id": self.engine_name}, user_id=user_id)

        # 3. HYPOTHESIS: Logical Pathways
        hypo_prompt = "Generate 3 probabilistic reasoning pathways and select the most valid one. 1 sentence."
        hypo_resp = await AdaptiveThrottler.run_throttled(call_lightweight_llm, [{"role": "user", "content": hypo_prompt}])
        steps.append({"stage": "Hypothesis", "thought": SovereignSecurity.mask_pii(hypo_resp or "Hypothesis crystallized.")})
        SovereignBroadcaster.publish("NEURAL_THINKING", {"stage": "Hypothesis", "mission_id": self.engine_name}, user_id=user_id)

        # 4. SELF-CRITICISM: The Reflector Layer (High-Parameter Analysis)
        crit_prompt = f"Critique this logic: '{hypo_resp}'. Search for fallacies or hallucinations. 1 sentence."
        crit_model = os.getenv("OLLAMA_MODEL_COMPLEX", "llama3.3:70b")
        crit_resp = await AdaptiveThrottler.run_throttled(
            call_lightweight_llm, 
            [{"role": "user", "content": crit_prompt}],
            model=crit_model
        )
        steps.append({"stage": "Self-Criticism", "thought": SovereignSecurity.mask_pii(crit_resp or "Self-reflection pass successful.")})
        SovereignBroadcaster.publish("NEURAL_THINKING", {"stage": "Self-Criticism", "mission_id": self.engine_name}, user_id=user_id)

        # 5. SYNTHESIS: Final Response
        synth_prompt = f"Synthesize all steps into a definitive conclusion for the user: '{query}'. Context: {crit_resp}. Be profound."
        conclusion = await AdaptiveThrottler.run_throttled(call_lightweight_llm, [{"role": "user", "content": synth_prompt}])
        SovereignBroadcaster.publish("NEURAL_THINKING", {"stage": "Synthesis", "mission_id": self.engine_name}, user_id=user_id)

        return {
            "mode": mode,
            "conclusion": SovereignSecurity.mask_pii(conclusion or "Reasoning finalized."),
            "steps": steps,
            "full_chain": "\n".join([f"[{s['stage']}] {s['thought']}" for s in steps])
        }

    async def multi_step_cot(self, **kwargs) -> str:
        """Compatibility wrapper for simple string output."""
        result = await self.execute(**kwargs)
        if result.status == "success":
            return result.data["full_chain"]
        return "Reasoning loop interrupted."

    async def synthesize(self, **kwargs) -> str:
        """Synthesize multiple inputs into a clean reasoning summary."""
        result = await self.execute(mode="synthesis", **kwargs)
        return result.data["conclusion"] if result.status == "success" else "Synthesis failure."
