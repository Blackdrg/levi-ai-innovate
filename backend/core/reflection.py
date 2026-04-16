"""
Sovereign Reflection Engine.
Evaluates outcomes through the critic and returns a structured fidelity verdict.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.agents.critic_agent import CriticAgent

logger = logging.getLogger(__name__)


class ReflectionEngine:
    def __init__(self):
        self.critic = CriticAgent()
        logger.info("[Reflection] Critic-backed reflection engine active.")

    async def evaluate(
        self,
        response: str,
        goal: Any,
        perception: Dict[str, Any],
        results: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        logger.info("[Reflection] Grading mission response: %s...", response[:50])

        objective = getattr(goal, "objective", str(goal))
        critique = await self.critic.evaluate(
            mission_id=perception.get("request_id") or perception.get("mission_id") or "reflection",
            objective=objective,
            result={
                "response": response,
                "results": [r.dict() if hasattr(r, "dict") else r for r in (results or [])],
                "context": perception.get("context", {}),
            },
        )

        fidelity = float(critique.get("fidelity_score", 0.0))
        issues = critique.get("issues", [])
        return {
            "score": fidelity,
            "confidence": fidelity,
            "fidelity": fidelity,
            "errors": issues,
            "validated": critique.get("is_valid", False),
            "metadata": {
                "breakdown": critique.get("breakdown", {}),
                "objective": objective,
            },
            "is_satisfactory": critique.get("is_valid", False),
            "critique": issues,
            "suggestions": [],
            "alignment_gap": max(0.0, 1.0 - fidelity),
        }

    async def self_correct(self, response: str, evaluation: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> str:
        if evaluation.get("is_satisfactory"):
            return response

        from .planner import call_lightweight_llm

        prompt = (
            f"Objective: {getattr(goal, 'objective', str(goal))}\n"
            f"Draft: {response}\n"
            f"Critique: {evaluation.get('critique', [])}\n"
            "Produce an improved version that resolves the identified issues."
        )
        return await call_lightweight_llm([{"role": "user", "content": prompt}])

    async def assess_mission_failure(self, mission_id: str, results: List[Any]):
        logger.warning("[Reflection] Commencing forensic audit for failed mission: %s", mission_id)
        anomalies = []
        for res in results:
            success = getattr(res, "success", True) if not isinstance(res, dict) else res.get("success", True)
            if not success:
                anomalies.append({
                    "agent": getattr(res, "agent", "unknown") if not isinstance(res, dict) else res.get("agent", "unknown"),
                    "error": str(getattr(res, "error", "Unknown anomaly")) if not isinstance(res, dict) else str(res.get("error", "Unknown anomaly")),
                })
        logger.info("[Reflection] Failure audit complete for %s. anomalies=%s", mission_id, len(anomalies))
