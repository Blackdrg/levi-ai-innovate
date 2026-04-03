import logging
import asyncio
from typing import Dict, Any, List, Optional
from ..tool_registry import call_tool
from ..orchestrator_types import ToolResult

logger = logging.getLogger(__name__)

class ReflectionEngine:
    """
    LeviBrain v8: Reflection Engine (Critic v2)
    Self-correction loop to evaluate and enhance reasoning quality.
    """

    async def evaluate(self, response: str, goal: Any, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        LeviBrain v8: High-Fidelity Mission Evaluation.
        Measures Alignment, Grounding, and Resonance.
        """
        user_input = perception.get("input", "")
        context = perception.get("context", {})
        
        logger.info("[V8 Reflection] Initiating qualitative audit...")
        
        # 1. Auditor Invocation (CriticAgentV8)
        audit_raw = await call_tool("critic_agent", {
            "goal": goal.objective,
            "success_criteria": goal.success_criteria,
            "response": response,
            "user_input": user_input
        }, context)
        
        # 2. Extract High-Fidelity Metrics
        metrics = audit_raw.get("data", {})
        fidelity_score = metrics.get("quality_score", 0.5)
        issues = metrics.get("issues", [])
        fix_strategy = metrics.get("fix", "Apply general refinement.")
        is_safe = not metrics.get("hallucination_detected", True)
        
        # 3. v8 Threshold Logic
        is_satisfactory = fidelity_score >= 0.85 and is_safe
        
        return {
            "score": fidelity_score,
            "issues": issues,
            "fix": fix_strategy,
            "is_satisfactory": is_satisfactory,
            "metrics": metrics.get("metrics", {})
        }

    async def self_correct(self, response: str, evaluation: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> str:
        """
        Triggers an Adaptive Refinement pass based on audit failure.
        This represents a 'Correction Wave' in the cognitive pipeline.
        """
        if evaluation["is_satisfactory"]:
            return response
            
        logger.warning("[V8 Reflection] Mission Fidelity Failure (%.2f). Executing Correction Wave...", evaluation["score"])
        
        context = perception.get("context", {})
        
        # High-Fidelity Refinement Pass
        correction_raw = await call_tool("chat_agent", {
            "input": f"ORIGINAL INPUT: {perception['input']}\n\nDRAFT RESPONSE: {response}\n\nAUDIT ISSUES: {evaluation['issues']}\n\nFIX STRATEGY: {evaluation['fix']}",
            "mood": "precise",
            "context": "MISSION_REFINEMENT"
        }, context)
        
        return correction_raw.get("message", response)
