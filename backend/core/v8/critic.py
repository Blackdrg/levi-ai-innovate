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
        LeviBrain v8.7: Evolutionary qualitative audit.
        Adjusts strictness based on historical fragility and mission complexity.
        """
        user_input = perception.get("input", "")
        context = perception.get("context", {})
        
        # 1. Pull Evolutionary Weight (0.1 to 1.0)
        sc_weight = getattr(goal, "self_correction_weight", 0.5)
        hyper_reflection = sc_weight > 0.8
        
        logger.info(f"[V8 Reflection] Initiating qualitative audit (Weight: {sc_weight:.2f})...")
        
        # 2. Auditor Invocation (CriticAgentV8)
        # We inject the hyper_reflection flag into context to trigger deeper audit logic in the agent
        audit_context = {**context, "hyper_reflection": hyper_reflection, "sc_weight": sc_weight}
        
        audit_raw = await call_tool("critic_agent", {
            "goal": goal.objective,
            "success_criteria": goal.success_criteria,
            "response": response,
            "user_input": user_input,
            "rigor": "exhaustive" if hyper_reflection else "standard"
        }, audit_context)
        
        # 3. Extract High-Fidelity Metrics
        metrics = audit_raw.get("data", {})
        fidelity_score = metrics.get("quality_score", 0.5)
        issues = metrics.get("issues", [])
        fix_strategy = metrics.get("fix", "Apply general refinement.")
        is_safe = not metrics.get("hallucination_detected", True)
        
        # 4. Dynamic Threshold Logic
        # High-fragility missions require higher fidelity (up to 0.95)
        threshold = 0.80 + (sc_weight * 0.15)
        is_satisfactory = fidelity_score >= threshold and is_safe
        
        if hyper_reflection and not is_satisfactory:
            logger.warning("[V8 Reflection] Hyper-Reflection Triggered: Fidelity (%.2f) < Threshold (%.2f)", fidelity_score, threshold)
        
        return {
            "score": fidelity_score,
            "issues": issues,
            "fix": fix_strategy,
            "is_satisfactory": is_satisfactory,
            "threshold": threshold,
            "metrics": metrics.get("metrics", {})
        }

    async def self_correct(self, response: str, evaluation: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> str:
        """Adaptive Refinement pass with Evolutionary context."""
        if evaluation["is_satisfactory"]:
            return response
            
        logger.warning("[V8 Reflection] Mission Fidelity Gap (%.2f < %.2f). Executing Correction Wave...", 
                       evaluation["score"], evaluation["threshold"])
        
        context = perception.get("context", {})
        sc_weight = getattr(goal, "self_correction_weight", 0.5)
        
        # High-Fidelity Refinement Pass
        correction_raw = await call_tool("chat_agent", {
            "input": f"ORIGINAL INPUT: {perception['input']}\n\nDRAFT RESPONSE: {response}\n\nAUDIT ISSUES: {evaluation['issues']}\n\nFIX STRATEGY: {evaluation['fix']}",
            "mood": "precise" if sc_weight > 0.6 else "balanced",
            "context": "MISSION_REFINEMENT",
            "rigor_weight": sc_weight
        }, context)
        
        return correction_raw.get("message", response)

    async def suggest_system_patch(self, failures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        v9.5: Recursive Self-Correction.
        Analyzes a batch of failures to suggest a logical patch for the Sovereign system.
        """
        if not failures:
            return None
            
        logger.info(f"[V9.5 Reflection] Analyzing {len(failures)} failures for recursive self-correction...")
        
        failure_context = "\n".join([f"Input: {f['input']} | Issue: {f['reasons']}" for f in failures])
        
        prompt = (
            "You are the LEVI Recursive Architect. Analyze the following recurring system failures:\n\n"
            f"{failure_context}\n\n"
            "Suggest a specific logical improvement or 'System Patch' to prevent these issues.\n"
            "Your patch should target one of the following domains:\n"
            "- PERCEPTION (Intent detection)\n"
            "- PLANNING (DAG generation)\n"
            "- DECISION (Priority scoring)\n"
            "- ENGINE (Deterministic logic)\n\n"
            "Response format (JSON): {'domain': '', 'reasoning': '', 'patch_logic': '', 'risk_score': 0.0}"
        )
        
        # We use a high-fidelity model for recursive patching
        from backend.engines.chat.generation import SovereignGenerator
        generator = SovereignGenerator()
        
        patch_raw = await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Recursive Architect (v9.5)."},
            {"role": "user", "content": prompt}
        ], temperature=0.1)
        
        try:
            import json
            return json.loads(patch_raw.strip().replace("```json", "").replace("```", ""))
        except:
            logger.warning("[V9.5 Reflection] Failed to parse patch proposal.")
            return None
