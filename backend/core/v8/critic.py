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
        """Runs a multi-metric evaluation of the response quality."""
        user_input = perception.get("input", "")
        context = perception.get("context", {})
        
        # 1. Critic Call
        critic_raw = await call_tool("critic_agent", {
            "goal": goal.objective,
            "success_criteria": goal.success_criteria,
            "response": response,
            "user_input": user_input
        }, context)
        
        # 2. Extract Metrics
        metrics = critic_raw.get("data", {})
        quality_score = metrics.get("quality_score", 0.5)
        issues = metrics.get("issues", [])
        fix_strategy = metrics.get("fix", "No fix needed")
        
        return {
            "score": quality_score,
            "issues": issues,
            "fix": fix_strategy,
            "is_satisfactory": quality_score >= 0.85
        }

    async def self_correct(self, response: str, evaluation: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> str:
        """Applies a correction pass based on critic results."""
        if evaluation["is_satisfactory"]:
            return response
            
        logger.info("[ReflectionEngine] Low quality response (%.2f). Correcting...", evaluation["score"])
        
        context = perception.get("context", {})
        correction_raw = await call_tool("chat_agent", {
            "input": f"Original Input: {perception['input']}\n\nDraft Response: {response}\n\nIdentified Issues: {evaluation['issues']}\n\nTask: {evaluation['fix']}",
            "mood": "precise"
        }, context)
        
        return correction_raw.get("message", response)
