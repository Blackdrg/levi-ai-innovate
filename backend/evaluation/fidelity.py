"""
Sovereign Cognitive Fidelity v8.
LLM-based Critic for measuring response quality and goal alignment.
"""

import logging
import json
from typing import Dict, Any, List
from backend.core.planner import call_lightweight_llm

logger = logging.getLogger(__name__)

class FidelityCritic:
    """
    The High-Fidelity Critic (Level 3 Cognitive Feedback).
    Evaluates the Brain's output against the mission objective.
    """

    @staticmethod
    async def evaluate_mission(
        user_query: str,
        response: str,
        goals: List[str],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Performs a multi-dimensional fidelity audit.
        Dimensions: Goal Alignment, Factual Grounding, Tone Resonance.
        """
        
        critic_prompt = (
            "You are the Sovereign Critic v8. Audit this LEVI-AI mission response.\n"
            f"User Vision: {user_query}\n"
            f"Mission Goals: {', '.join(goals)}\n"
            f"Specialized Agent Results: {json.dumps(tool_results[:5])}\n"
            f"LEVI Response: {response}\n\n"
            "Evaluate on 0.0 to 1.0:\n"
            "1. Goal Alignment (Did we do what was asked?)\n"
            "2. Factual Grounding (Is it supported by agent results?)\n"
            "3. Tone Resonance (Is it philosophical and unified?)\n\n"
            "Output JSON: {\"alignment\": 0.0, \"grounding\": 0.0, \"resonance\": 0.0, \"critique\": \"...\"}"
        )

        try:
            raw_eval = await call_lightweight_llm([{"role": "system", "content": critic_prompt}])
            evaluation = json.loads(raw_eval.strip())
            
            # Weighted Fidelity Score
            fidelity = (
                evaluation.get("alignment", 0.0) * 0.5 +
                evaluation.get("grounding", 0.0) * 0.3 +
                evaluation.get("resonance", 0.0) * 0.2
            )
            
            evaluation["fidelity_score"] = round(fidelity, 3)
            return evaluation
        except Exception as e:
            logger.error(f"[FidelityCritic] Evaluation failed: {e}")
            return {"fidelity_score": 0.0, "error": str(e)}
