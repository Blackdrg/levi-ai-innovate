"""
Sovereign Reflection Engine v8.
Evaluates and enhances reasoning quality through a critic-correction loop.
Based on LeviBrain v8 Critic v2.
"""

from typing import Dict, Any, List
from .agent_registry import AgentRegistry
from .orchestrator_types import ToolResult
from .goal_engine import Goal
from backend.pipelines.learning import learning_system


class ReflectionEngine:
    """
    LeviBrain v8: Reflection Engine (Critic v2).
    Multi-dimensional fidelity audit with self-correction and automated reporting.
    """

    async def evaluate(self, response: str, goal: Goal, perception: Dict[str, Any], results: List[ToolResult]) -> Dict[str, Any]:
        """Runs a high-fidelity mission audit using the v8 CriticAgent (Multi-Agent Debate)."""
        user_input = perception.get("input", "")
        
        # 1. Dispatch to v8 Critic Agent
        critic_context = {
            "goal": goal.objective,
            "success_criteria": goal.success_criteria,
            "response": response,
            "user_input": user_input,
            "tool_results": [r.dict() for r in results]
        }
        
        audit_res = await AgentRegistry.dispatch("critic", critic_context)
        
        score = fidelity
        issues = audit_res.data.get("issues", ["High-fidelity audit failed."])
        
        # 3. LEVI Learning Bridge: Log failures for prompt optimization
        if score < 0.6:
            import asyncio
            asyncio.create_task(learning_system.log_failure(user_input, response, score, issues))

        return {
            "score": score,
            "issues": issues,
            "is_satisfactory": audit_res.get("success", False) and score >= 0.8,
            "raw_eval": audit_res.data,
            "fix": audit_res.data.get("fix", "No fix identified.")
        }

    async def self_correct(self, response: str, evaluation: Dict[str, Any], goal: Goal, perception: Dict[str, Any]) -> str:
        """Applies a high-precision correction pass based on the fidelity audit."""
        if evaluation["is_satisfactory"]:
            return response
            
        logger.info("[ReflectionEngine] Low fidelity mission (%.2f). Correcting...", evaluation["score"])
        
        context = perception.get("context", {})
        correction_raw = await call_tool("chat_agent", {
            "input": f"Original Vision: {perception['input']}\n\nDraft: {response}\n\nCritic Analysis: {evaluation['issues'][0]}\n\nObjective: {goal.objective}",
            "mood": "precise"
        }, context)
        
        return correction_raw.message if isinstance(correction_raw, ToolResult) else correction_raw.get("message", response)
