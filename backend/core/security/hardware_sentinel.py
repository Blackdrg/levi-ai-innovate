import logging
import asyncio
import hashlib
from typing import Dict, Any
from backend.kernel.kernel_wrapper import kernel
from backend.utils.event_bus import sovereign_event_bus

logger = logging.getLogger(__name__)

class HardwareSentinel:
    """
    Sovereign v22.1: Hardware-Bound Integrity Monitor.
    Audits the kernel's PCR measurements and mission-signing keys.
    If a deviation is detected, it triggers a 'Cognitive Freeze'.
    """
    def __init__(self):
        self._is_breached = False
        self._reference_pcr = None

    async def start_audit_loop(self):
        """Active background monitoring of hardware residency proofs."""
        logger.info("🛡️ [Sentinel] Hardware Sentinel Awakening...")
        
        # 1. Capture Reference PCR (Measured Boot)
        self._reference_pcr = kernel.get_pcr_measurement(0)
        logger.info(f"🛡️ [Sentinel] Measured Boot Reference: {self._reference_pcr[:16]}...")

        while True:
            try:
                await self.perform_integrity_check()
                await asyncio.sleep(60) # High-trust interval
            except Exception as e:
                logger.error(f"[Sentinel] Integrity Audit Failure: {e}")
                await asyncio.sleep(5)

    async def perform_integrity_check(self):
        """Verifies that the root-of-trust is still valid."""
        current_pcr = kernel.get_pcr_measurement(0)
        
        if current_pcr != self._reference_pcr:
            logger.critical("🚨 [SENTINEL] HARDWARE INTEGRITY BREACH! PCR0 DIVERGENCE DETECTED.")
            logger.critical(f"Expected: {self._reference_pcr} | Received: {current_pcr}")
            await self._trigger_freeze("PCR_MISMATCH")
            return

        # 2. Check Signing Authority
        pub_key = kernel.get_signing_key_public()
        if len(pub_key) < 32 or pub_key == b"00"*16:
             logger.warning("⚠️ [Sentinel] Signing Authority in fallback/degraded mode.")
        
        logger.debug("🛡️ [Sentinel] Integrity Verify: PASSED")

    async def _trigger_freeze(self, reason: str):
        """Halts all mission dispatch to prevent sovereign data leakage."""
        if self._is_breached: return
        self._is_breached = True
        
        logger.critical(f"🛑 [SENTINEL] COGNITIVE FREEZE ENGAGED: {reason}")
        
        await sovereign_event_bus.emit("system_errors", {
            "type": "HARDWARE_BREACH",
            "reason": reason,
            "status": "FREEZE_ACTIVE"
        })
        
        # In a real OS, we would trigger a kernel-level halt here.
        # For LEVI, we tell the Orchestrator to reject all DAGs.
        from backend.core.orchestrator import orchestrator
        if orchestrator:
            orchestrator.paused = True
            
hardware_sentinel = HardwareSentinel()
