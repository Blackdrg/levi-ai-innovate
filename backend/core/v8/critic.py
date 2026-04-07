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
        LeviBrain v13.1 Bias-Aware Qualitative Audit.
        Implements Shadow Critic cross-verification and Fidelity Badging.
        """
        mission_id = perception.get("context", {}).get("mission_id", "audit")
        user_id = perception.get("user_id", "default_user")
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
        
        # 🛡️ Shadow Critic Intervention (v13.1 Phase 5)
        # We invoke an independent model (e.g., phi3:mini) to detect self-referential bias
        shadow_audit_context = {**audit_context, "preferred_model": "phi3:mini"} # Force lightweight shadow model
        shadow_audit = await call_tool("critic_agent", {
            "goal": goal.objective,
            "success_criteria": goal.success_criteria,
            "response": response,
            "user_input": user_input,
            "rigor": "standard"
        }, shadow_audit_context)

        # 3. Extract High-Fidelity Metrics
        metrics = audit_raw.get("data", {})
        fidelity_score = metrics.get("quality_score", 0.5)
        shadow_score = shadow_audit.get("data", {}).get("quality_score", 0.5)
        
        # 🧪 Bias Detection Logic
        divergence = abs(fidelity_score - shadow_score)
        
        # 🛡️ v13.1 Phase 7: Personalized Calibration Offset
        offset = await self._get_calibration_offset(user_id)
        fidelity_score = max(0.0, min(1.0, fidelity_score + offset))
        
        requires_hitl = divergence > 0.15
        
        # Log calibration data for weekly offset calculation
        asyncio.create_task(self._log_calibration(mission_id, fidelity_score, shadow_score, divergence))
        issues = metrics.get("issues", [])
        fix_strategy = metrics.get("fix", "Apply general refinement.")
        is_safe = not metrics.get("hallucination_detected", True)
        
        # 4. Dynamic Threshold Logic
        # High-fragility missions require higher fidelity (up to 0.95)
        threshold = 0.80 + (sc_weight * 0.15)
        is_satisfactory = fidelity_score >= threshold and is_safe and not requires_hitl
        
        # 🏷️ Fidelity Badge Allocation (v13.1 Limbo Gap Correction)
        if fidelity_score >= 0.85:
            badge = "VERIFIED"
        elif fidelity_score >= 0.65:
            badge = "REVIEWED"
        else:
            badge = "DRAFT"

        if requires_hitl:
            logger.warning("[V13.1 Bias] Primary/Shadow Divergence detected (%.2f). Blocking auto-crystallization.", divergence)

        if hyper_reflection and not is_satisfactory:
            logger.warning("[V8 Reflection] Hyper-Reflection Triggered: Fidelity (%.2f) < Threshold (%.2f)", fidelity_score, threshold)
        
        return {
            "score": fidelity_score,
            "shadow_score": shadow_score,
            "divergence": divergence,
            "badge": badge,
            "requires_hitl": requires_hitl,
            "issues": issues,
            "fix": fix_strategy,
            "is_satisfactory": is_satisfactory,
            "threshold": threshold,
            "metrics": metrics.get("metrics", {})
        }

    async def _log_calibration(self, mission_id: str, primary: float, shadow: float, divergence: float):
        """Persists calibration drift to Postgres."""
        try:
            from backend.db.postgres_db import PostgresDB
            from backend.db.models import CriticCalibration
            async with PostgresDB._session_factory() as session:
                calibration = CriticCalibration(
                    mission_id=mission_id,
                    user_id=mission_id.split("_")[0] if "_" in mission_id else "default_user", # Heuristic for user_id
                    primary_score=primary,
                    shadow_score=shadow,
                    divergence=divergence
                )
                session.add(calibration)
                await session.commit()
        except Exception as e:
            logger.error(f"[BiasControl] Failed to log calibration: {e}")

    async def _get_calibration_offset(self, user_id: str) -> float:
        """Fetches the personalized calibration offset for the user, with a global fallback."""
        try:
            from backend.db.postgres_db import PostgresDB
            from backend.db.models import UserCalibration
            from sqlalchemy import select
            
            async with PostgresDB._session_factory() as session:
                # 1. Check User specific
                stmt = select(UserCalibration.bias_offset).where(UserCalibration.user_id == user_id)
                res = await session.execute(stmt)
                offset = res.scalar_one_or_none()
                
                if offset is not None:
                    return float(offset)
                
                # 2. Fallback to Global
                stmt = select(UserCalibration.bias_offset).where(UserCalibration.user_id == "global")
                res = await session.execute(stmt)
                offset = res.scalar_one_or_none()
                
                return float(offset) if offset is not None else 0.0
        except Exception as e:
            logger.error(f"[BiasControl] Failed to fetch offset for {user_id}: {e}")
            return 0.0

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
