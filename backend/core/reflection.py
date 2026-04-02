"""
Sovereign Reflection Engine v8.
Evaluates and enhances reasoning quality through a critic-correction loop.
Based on LeviBrain v8 Critic v2.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from .tool_registry import call_tool
from .orchestrator_types import ToolResult
from .goal_engine import Goal
from backend.evaluation.fidelity import FidelityCritic
from backend.evaluation.evaluator import AutomatedEvaluator

class ReflectionEngine:
    """
    LeviBrain v8: Reflection Engine (Critic v2).
    Multi-dimensional fidelity audit with self-correction and automated reporting.
    """

    async def evaluate(self, response: str, goal: Goal, perception: Dict[str, Any], results: List[ToolResult]) -> Dict[str, Any]:
        """Runs a high-fidelity fidelity audit using the v8 Critic."""
        user_input = perception.get("input", "")
        
        # 1. Fidelity Audit (LLM + Heuristics)
        # Bridge ToolResult results for the critic
        tool_data = [{"tool": r.tool, "data": r.data} for r in results]
        
        evaluation = await FidelityCritic.evaluate_mission(
            user_query=user_input,
            response=response,
            goals=[goal.objective] + goal.success_criteria,
            tool_results=tool_data
        )
        
        # 2. Enrich for v8 Reflection Loop
        fidelity = evaluation.get("fidelity_score", 0.0)
        
        return {
            "score": fidelity,
            "issues": [evaluation.get("critique", "No specific issues identified.")],
            "is_satisfactory": fidelity >= 0.85, # Production-grade threshold
            "raw_eval": evaluation
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
