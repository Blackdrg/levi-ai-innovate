import os
import logging
import asyncio
import time
from typing import Optional, Dict, Any
from backend.services.ollama_health import ollama_monitor
from backend.services.rollback_service import rollback_service
from backend.db.redis_client import r as redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

class AutonomousHealthMonitor:
    """
    Sovereign v15.0: The 'Dead Man's Switch'.
    Continuously monitors system health (VRAM, LLM, DCN) and triggers 
    autonomous rollbacks if failure thresholds are breached.
    """
    def __init__(self):
        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None
        self.failure_counters = {
            "ollama": 0,
            "vram": 0,
            "dcn": 0
        }
        self.FAIL_THRESHOLD = int(os.getenv("HEALTH_FAIL_THRESHOLD", "5")) # Sequential failures before rollback
        self.CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30")) # Seconds

    async def start(self):
        if self._is_running: return
        self._is_running = True
        self._check_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"🛰️ [HealthMonitor] Autonomous monitoring active (Threshold: {self.FAIL_THRESHOLD})")

    async def stop(self):
        self._is_running = False
        if self._check_task:
            self._check_task.cancel()
            try: await self._check_task
            except asyncio.CancelledError: pass

    async def _monitor_loop(self):
        """Infinite loop for autonomous health checks."""
        while self._is_running:
            try:
                await self._perform_checks()
            except Exception as e:
                logger.error(f"[HealthMonitor] Check loop error: {e}")
            
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def _perform_checks(self):
        """Coordinates various system health checks."""
        
        # 1. Ollama Health
        ollama_health = await ollama_monitor.check_health()
        if ollama_health["status"] != "healthy":
            self.failure_counters["ollama"] += 1
            logger.warning(f"⚠️ [HealthMonitor] Ollama anomaly detected ({self.failure_counters['ollama']}/{self.FAIL_THRESHOLD})")
        else:
            self.failure_counters["ollama"] = 0

        # 2. VRAM Pressure
        from backend.main import orchestrator as brain
        if brain:
            vram_pressure = await brain.check_vram_pressure()
            if vram_pressure >= 1.0: # 1.0 means critical/OOM saturation (P0 Hardening)
                self.failure_counters["vram"] += 1
                logger.warning(f"⚠️ [HealthMonitor] VRAM Saturation detected ({self.failure_counters['vram']}/{self.FAIL_THRESHOLD})")
            else:
                self.failure_counters["vram"] = 0
        else:
             logger.debug("[HealthMonitor] Orchestrator not yet initialized. Skipping VRAM check.")
        
        # 3. Decision: Trigger Rollback?
        for cause, count in self.failure_counters.items():
            if count >= self.FAIL_THRESHOLD:
                await self._trigger_autonomous_action(cause)
                self.failure_counters[cause] = 0 # Reset after trigger

    async def _trigger_autonomous_action(self, cause: str):
        """Triggers a full-stack rollback without human intervention."""
        logger.critical(f"🚨 [HealthMonitor] CRITICAL SYSTEM FAILURE: {cause.upper()}. Triggering autonomous rollback across the cluster.")
        
        # In v15.0, we trigger rollback for ALL active missions on this node/cluster
        # We can simulate this by fetching all active users or using a system-wide abort
        
        try:
            # Note: For now, we use a placeholder user_id or trigger a global signal
            # The RollbackService handles the GitHub dispatch which is cluster-wide
            await rollback_service.trigger_emergency_rollback(
                user_id="SYSTEM_AUTONOMOUS", 
                reason=f"Autonomous Rollback: {cause.upper()} failure threshold exceeded."
            )
            
            # Additional logic: Mark node as 'DRAINING' in DCN pulse
            if HAS_REDIS:
                redis_client.set("dcn:node:status", "DRAINING", ex=300)
                
        except Exception as e:
            logger.error(f"[HealthMonitor] Failed to trigger autonomous action: {e}")

health_monitor = AutonomousHealthMonitor()
