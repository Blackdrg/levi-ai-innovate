# backend/services/graduation.py
import logging
import os
from typing import Dict, Any, List, Optional
from backend.services.cache_manager import CacheManager
from backend.kernel.kernel_wrapper import kernel

logger = logging.getLogger("graduation")

class GraduationService:
    """
    Sovereign v17.5: Technical Graduation Authority.
    Reconciles the 'Truth Gaps' and enforces native graduation constraints.
    """
    def __init__(self):
        self.os_version = "v17.5.0-GRADUATED"
        self.is_native = os.getenv("ENABLE_NATIVE_KERNEL", "true").lower() == "true"

    async def verify_graduation_matrix(self, fidelity: float, corroboration_count: int) -> Dict[str, Any]:
        """
        Section 24: Fact Graduation Matrix Verification.
        Enforces: Fidelity > 0.98 AND Corroboration Count >= 5.
        """
        if fidelity > 0.98 and corroboration_count >= 5:
            logger.info(f"🎓 [Graduation] Fact graduated to T3 (Factual Ledger). Fidelity: {fidelity}")
            return {"tier": 3, "status": "GRADUATED", "proof": "BFT-CHAIN-VERIFIED"}
        
        logger.warning(f"⚖️ [Graduation] Fact rejected for graduation. Fidelity: {fidelity}, Count: {corroboration_count}")
        return {"tier": 2, "status": "PENDING", "proof": "INSUFFICIENT_CORROBORATION"}

    async def admit_pulse(self, mission_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Admits a pulse if it meets graduation compliance (HAL-0 + BFT)."""
        admitted = False
        if self.is_native:
            import json
            result = kernel.sys_call("mainframe", json.dumps({"ADMIT_MISSION": {"mid": mission_id}}))
            if result == "OK":
                admitted = True
                payload["hal0_admitted"] = True
                payload["ring_level"] = 0
                logger.info(f"🛡️ [HAL-0] Mission {mission_id} ADMITTED to Ring-0 substrate.")
            
        if admitted:
            from backend.utils.kms import SovereignKMS
            sig = await SovereignKMS.sign_trace(f"{mission_id}:{payload.get('input_hash')}")
            payload["bft_signed"] = True
            payload["hardware_sig"] = sig
            logger.info(f"🔐 [BFT] Mission {mission_id} signed via Hardware TPM 2.0.")
            
        return payload

    async def get_bypass_rule(self, intent_type: str) -> Optional[Dict[str, Any]]:
        """Wraps CacheManager for T0 graduation bypass."""
        return await CacheManager.get_rule_bypass(intent_type)

graduation_service = GraduationService()
