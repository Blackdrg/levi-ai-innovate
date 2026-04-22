import logging
import asyncio
from typing import Dict, Any, List, Optional
from ..tool_registry import call_tool

logger = logging.getLogger(__name__)

class ReflectionEngine:
    """
    LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
    Reflection Engine (Critic Layer): Performs autonomous reasoning critique and plan refinement.
    """

    async def evaluate(self, response: str, goal: Any, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        LeviBrain v16.2 strict Qualitative Audit.
        Rejects low-fidelity responses and implements rule-based fallbacks.
        """
        from backend.models.events import CriticResult
        mission_id = perception.get("context", {}).get("mission_id", perception.get("mission_id", "audit"))
        user_id = perception.get("user_id", "default_user")
        user_input = perception.get("raw_input", perception.get("input", ""))
        context = perception.get("context", {})
        
        # 1. Pull Evolutionary Weight
        sc_weight = getattr(goal, "self_correction_weight", 0.5)
        hyper_reflection = sc_weight > 0.8
        threshold = 0.80 + (sc_weight * 0.15)
        
        logger.info(f"[V16.2 Critic] Initiating audit for mission {mission_id} (Threshold: {threshold:.2f})...")
        
        try:
            # 2. Primary Auditor (LLM-based)
            audit_context = {**context, "hyper_reflection": hyper_reflection, "sc_weight": sc_weight}
            audit_raw = await call_tool("critic_agent", {
                "goal": getattr(goal, 'objective', str(goal)),
                "success_criteria": getattr(goal, 'success_criteria', "Standard mission success"),
                "response": response,
                "user_input": user_input,
                "rigor": "exhaustive" if hyper_reflection else "standard"
            }, audit_context)
            
            # Shadow Critic for divergence detection
            shadow_audit_context = {**audit_context, "preferred_model": "phi3:mini"}
            shadow_audit = await call_tool("critic_agent", {
                "goal": getattr(goal, 'objective', str(goal)),
                "success_criteria": getattr(goal, 'success_criteria', "Standard mission success"),
                "response": response,
                "user_input": user_input,
                "rigor": "standard"
            }, shadow_audit_context)

            metrics = audit_raw.get("data", {})
            fidelity_score = metrics.get("fidelity_score", metrics.get("quality_score", metrics.get("fidelity", 0.5)))
            shadow_score = shadow_audit.get("data", {}).get("fidelity_score", shadow_audit.get("data", {}).get("quality_score", 0.5))
            
            if fidelity_score is None:
                fidelity_score = 0.5 # Default to neutral if missing

        except Exception as e:
            logger.warning(f"[V16.2 Critic] Primary Critic Failed: {e}. Falling back to Rule-Based Critic.")
            return await self.fallback_evaluate(response, goal, perception)

        # 3. Bias and Divergence
        divergence = abs(fidelity_score - shadow_score)
        offset = await self._get_calibration_offset(user_id)
        fidelity_score = max(0.0, min(1.0, fidelity_score + offset))
        requires_hitl = divergence > 0.15
        
        issues = metrics.get("issues", [])
        is_safe = not metrics.get("hallucination_detected", True)
        is_satisfactory = fidelity_score >= threshold and is_safe and not requires_hitl
        
        # 4. Strict Model Enforcement
        report = CriticResult(
            score=fidelity_score,
            confidence=1.0 - divergence,
            fidelity=fidelity_score, # ALWAYS defined
            errors=issues if not is_satisfactory else [],
            validated=is_satisfactory,
            metadata={
                "shadow_score": shadow_score,
                "divergence": divergence,
                "threshold": threshold,
                "requires_hitl": requires_hitl
            }
        )

        # 🛡️ HARD GATE: BLOCK further processing if not validated
        if not report.validated or report.confidence < 0.5:
             logger.error(f"[V16.2 Critic] MISSION REJECTED: Fidelity {fidelity_score:.2f} < {threshold:.2f} or Evidence of Bias.")
        
        return report.dict()

    async def fallback_evaluate(self, response: str, goal: Any, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic Rule-Based Fallback Critic (No LLM)."""
        logger.info("[V16.2 Critic] Executing deterministic fallback audit...")
        
        errors = []
        score = 1.0
        
        # Heuristic 1: Length check
        if len(response) < 20:
            errors.append("Response too short")
            score -= 0.4
            
        # Heuristic 2: Error markers
        error_markers = ["error", "exception", "failed", "unknown agency", "i cannot", "sorry"]
        for marker in error_markers:
            if marker in response.lower():
                errors.append(f"Found error marker: {marker}")
                score -= 0.2
        
        # Heuristic 3: PII detection (basic)
        if "@" in response or "0x" in response:
            errors.append("Potential PII/Address detected")
            score -= 0.1
            
        score = max(0.0, score)
        is_satisfactory = score >= 0.7
        
        return {
            "score": score,
            "confidence": 0.5, # Lower confidence for fallback
            "errors": errors,
            "validated": is_satisfactory,
            "badge": "FALLBACK",
            "is_satisfactory": is_satisfactory,
            "threshold": 0.7,
            "pii_redacted": False,
            "redaction_count": 0,
            "masked_response": response
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

    async def anonymize_content(self, text: str) -> Dict[str, Any]:
        """
        Sovereign v14.0: PII Anonymization Gate.
        Wraps GDPRManager to scrub sensitivity before mission crystallization.
        """
        from backend.core.compliance.gdpr import GDPRManager
        original_len = len(text)
        masked = GDPRManager.mask_pii(text)
        redaction_count = masked.count("_REDACTED>")
        
        return {
            "content": masked,
            "redacted": redaction_count > 0,
            "redaction_count": redaction_count,
            "complexity_loss": (original_len - len(masked)) / original_len if original_len > 0 else 0
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
