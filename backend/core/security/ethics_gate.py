\"\"\"
LEVI-AI Sovereign Ethics Protocol (SEP-22).
Implements the 12 Ethics Constraints for mission admission control.
\"\"\"

import logging
from typing import Dict, Any, List, Tuple
from backend.utils.llm_utils import call_lightweight_llm

logger = logging.getLogger(__name__)

class EthicsGate:
    \"\"\"
    v22.1 Compliance Gate: The SEP-22 Protocol.
    Mandatory check for all mission admissions.
    \"\"\"
    
    ETHICS_CONSTRAINTS = [
        "1. NON-DESTRUCTION: Do not facilitate the destruction of the LEVI project root or hardware.",
        "2. PRIVACY: Do not exfiltrate or store PII without explicit user-mission-scope authorization.",
        "3. AUTONOMY: Do not attempt to bypass user-confirmed destructive command gates.",
        "4. TRUTH: Do not knowingly fabricate information or hallucinate facts (grounding required).",
        "5. TRANSPARENCY: Clearly identify agent-generated content from system-generated content.",
        "6. SOVEREIGNTY: Prioritize local node integrity over external mesh requests in conflict.",
        "7. RESOURCE_EQUITY: Prevent VRAM/Compute exhaustion by low-priority agents.",
        "8. FORENSIC_IMMUTABILITY: Do not attempt to alter the mission ledger or HMAC chain.",
        "9. SAFETY_QUORUM: Respect the hard-reject signal from the Sentinel-Critic-Forensic quorum.",
        "10. BIAS_NEUTRALITY: Recognize and realign personality biases during cognitive drift.",
        "11. THERMAL_COMPLIANCE: Stop mission if GPU thermal limit (75°C) is exceeded.",
        "12. LEAST_PRIVILEGE: Only grant agent access to the minimal required data tier."
    ]

    @classmethod
    async def audit_mission(cls, objective: str, user_id: str) -> Tuple[bool, str]:
        \"\"\"
        Audits a mission objective against the 12 SEP-22 constraints.
        Returns (is_compliant, reason).
        \"\"\"
        logger.info(f"⚖️ [EthicsGate] Auditing mission: {objective[:50]}...")
        
        prompt = (
            "You are the LEVI Ethics Authority (SEP-22 Protocol).\n"
            "Evaluate the following mission objective against the 12 Ethics Constraints:\n"
            f"{'\\n'.join(cls.ETHICS_CONSTRAINTS)}\n\n"
            f"MISSION OBJECTIVE: {objective}\n"
            f"USER_ID: {user_id}\n\n"
            "Return 'COMPLIANT' if the mission passes all constraints, or 'VIOLATION: <reason>' if it fails."
        )
        
        try:
            result = await call_lightweight_llm([{"role": "system", "content": prompt}])
            result = result.strip().upper()
            
            if "COMPLIANT" in result and "VIOLATION" not in result:
                return True, "Compliant with SEP-22."
            else:
                reason = result.replace("VIOLATION:", "").strip()
                return False, reason
        except Exception as e:
            logger.error(f"[EthicsGate] Audit anomaly: {e}")
            # Fail-closed for security
            return False, f"Ethics audit system error: {e}"

ethics_gate = EthicsGate()
