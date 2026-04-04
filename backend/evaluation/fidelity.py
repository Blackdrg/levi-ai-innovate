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
    async def calculate_s(
        user_query: str,
        response: str,
        goals: List[str],
        agent_results: List[Any] # List of AgentResult or ToolResult
    ) -> Dict[str, Any]:
        """
        Sovereign v13.0: Formal Fidelity Score S Calculation.
        S = (0.4 * CriticScore) + (0.4 * MeanAgentFidelity) + (0.2 * MeanAgentConfidence)
        """
        # 1. Get Critic Evaluation
        critic_results = await FidelityCritic.evaluate_mission(user_query, response, goals, [r.dict() if hasattr(r, 'dict') else str(r) for r in agent_results])
        critic_score = critic_results.get("fidelity_score", 0.0)

        # 2. Aggregate Agent Performance
        if not agent_results:
            agent_fidelity = 0.0
            agent_confidence = 0.0
        else:
            fidelities = [getattr(r, "fidelity_score", 0.0) for r in agent_results]
            confidences = [getattr(r, "confidence", 1.0) for r in agent_results]
            agent_fidelity = sum(fidelities) / len(fidelities)
            agent_confidence = sum(confidences) / len(confidences)

        # 3. Final Weighted Score S
        s_score = (0.4 * critic_score) + (0.4 * agent_fidelity) + (0.2 * agent_confidence)
        s_score = round(min(max(s_score, 0.0), 1.0), 4)

        # 4. Adjudication Routing
        requires_manual_audit = s_score < 0.6
        circuit_break = s_score < 0.3
        
        return {
            "s_score": s_score,
            "critic": critic_results,
            "agent_avg_fidelity": agent_fidelity,
            "agent_avg_confidence": agent_confidence,
            "requires_manual_audit": requires_manual_audit,
            "circuit_break": circuit_break,
            "adjudication": "MANUAL_AUDIT_QUEUE" if requires_manual_audit else "AUTONOMOUS_PROMOTION"
        }

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
        from backend.core.planner import call_lightweight_llm
        
        critic_prompt = (
            "You are the Sovereign Critic v13. Audit this LEVI-AI mission response.\n"
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
