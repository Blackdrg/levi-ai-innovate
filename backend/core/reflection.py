"""
Sovereign Reflection Engine v16.1 [HARDENED].
Evaluates and enhances reasoning quality through a forensic critic-correction loop.
"""

import logging
from typing import Dict, Any, List, Optional

from backend.agents.critic_agent import CriticAgent, CriticInput
from .orchestrator_types import ToolResult
from .goal_engine import Goal

logger = logging.getLogger(__name__)

class ReflectionEngine:
    """
    Sovereign Reflection Engine v16.1.
    Utilizes a Critic Agent to assess mission fidelity and alignment.
    """

    def __init__(self):
        self.critic = CriticAgent()
        logger.info("[Reflection] Sovereign v16.1 Forensic Engine Active.")

    async def evaluate(self, response: str, goal: Any, perception: Dict[str, Any], results: List[Any]) -> Dict[str, Any]:
        """
        Sovereign v15.0: High-Fidelity Reflection.
        Dispatches to a Critic Agent to grade the mission outcome.
        """
        logger.info(f"🔍 [Reflection] Grading mission response: {response[:50]}...")
        
        # 1. Prepare Critic Input
        critic_input = CriticInput(
            objective=goal.objective,
            draft=response,
            context={
                "intent": perception.get("intent"),
                "results_count": len(results),
                "has_context": bool(perception.get("context"))
            }
        )
        
        # 2. Execute Critic Loop
        critic_result = await self.critic._run(critic_input)
        
        # 3. Extract Fidelity (v16.1 Fix: Extract from result dict)
        res_data = critic_result.get("data", {}) if isinstance(critic_result, dict) else getattr(critic_result, "data", {})
        fidelity = res_data.get("fidelity_score", 0.0) if isinstance(res_data, dict) else 0.0
        
        is_satisfactory = fidelity >= 0.8
        logger.info(f"📊 [Reflection] Fidelity: {fidelity:.2f} | Satisfactory: {is_satisfactory}")
        
        return {
            "is_satisfactory": is_satisfactory,
            "fidelity": fidelity,
            "critique": res_data.get("critique", "Forensic analysis unavailable."),
            "suggestions": res_data.get("suggestions", []),
            "alignment_gap": res_data.get("alignment_gap", 0.0)
        }

    async def self_correct(self, response: str, evaluation: Dict[str, Any], goal: Goal, perception: Dict[str, Any]) -> str:
        """Applies a high-precision correction pass based on the fidelity audit."""
        if evaluation["is_satisfactory"]:
            return response
            
        fidelity = evaluation.get("fidelity", 0.0)
        logger.info("[ReflectionEngine] Low fidelity mission (%.2f). Correcting...", fidelity)
        
        # In v16.1, we use a specialized refinement tool
        from .planner import call_lightweight_llm
        prompt = (
            f"Objective: {goal.objective}\n"
            f"Draft: {response}\n"
            f"Critique: {evaluation['critique']}\n"
            "Produce an improved version that resolves the identified issues."
        )
        correction = await call_lightweight_llm([{"role": "user", "content": prompt}])
        return correction

    async def assess_mission_failure(self, mission_id: str, results: List[Any]):
        """
        Sovereign v16.1: Forensic Failure Assessment (SAGA Trigger).
        Analyzes why a mission failed and initiates compensation/rollback if required.
        """
        logger.warning(f"🚨 [Reflection] Commencing Forensic Audit for FAILED mission: {mission_id}")
        
        # 1. Identify failure bottlenecks
        anomalies = []
        for res in results:
            success = getattr(res, "success", True) if not isinstance(res, dict) else res.get("success", True)
            if not success:
                anomalies.append({
                    "agent": getattr(res, "agent", "unknown") if not isinstance(res, dict) else res.get("agent", "unknown"),
                    "output": str(getattr(res, "output", ""))[:500] if not isinstance(res, dict) else str(res.get("output", ""))[:500],
                    "error": str(getattr(res, "error", "Unknown anomaly")) if not isinstance(res, dict) else str(res.get("error", "Unknown anomaly"))
                })
        
        # 2. Log Forensic Evidence
        logger.info(f"[Forensics] Detected {len(anomalies)} anomalies in mission {mission_id}.")
        
        # 3. Trigger SAGA Compensation (Simplified)
        if anomalies:
            try:
                from backend.core.saga_manager import saga_manager
                await saga_manager.compensate(mission_id, anomalies)
            except ImportError:
                logger.error("[Forensics] SagaManager unavailable. Rollback skipped.")
            
        logger.info(f"✅ [Reflection] Forensic failure assessment complete for {mission_id}.")
