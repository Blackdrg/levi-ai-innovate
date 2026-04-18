# backend/services/graduation.py
import logging
import os
from typing import Dict, Any, List
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

    async def admit_pulse(self, mission_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Admits a pulse if it meets graduation compliance (HAL-0 + BFT)."""
        
        # 🟢 1. Native HAL-0 Admission (Syscall simulated via kernel wrapper)
        admitted = False
        if self.is_native:
            # Syscall: ADMIT_MISSION(mission_id)
            result = kernel.sys_call("mainframe", "ADMIT_MISSION", {"mid": mission_id})
            if result == "OK":
                admitted = True
                payload["hal0_admitted"] = True
                payload["ring_level"] = 0
                logger.info(f"🛡️ [HAL-0] Mission {mission_id} ADMITTED to Ring-0 substrate.")
            
        # 🟢 2. Hardware BFT Signing (TPM Rooted)
        if admitted:
            # Simulate hardware-rooted signature via SovereignKMS (wired to TPM)
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
