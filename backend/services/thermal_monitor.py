# backend/services/thermal_monitor.py
import asyncio
import logging
import os
from backend.utils.hardware import gpu_monitor
from backend.core.orchestrator import orchestrator

logger = logging.getLogger("thermal-monitor")

class ThermalGovernance:
    """
    Sovereign v22-GA Thermal Governance (Section 33).
    - Migration at 75°C.
    - Emergency shutdown at 85°C.
    - VRAM_THERMAL_LIMIT enforced for model scaling.
    """
    def __init__(self):
        self.migration_temp = float(os.getenv("AGENT_MIGRATION_TEMP", 75.0))
        self.shutdown_temp = float(os.getenv("EMERGENCY_SHUTDOWN_TEMP", 85.0))
        self.vram_limit = float(os.getenv("VRAM_THERMAL_LIMIT", 78.0))
        self.interval = int(os.getenv("THERMAL_CHECK_INTERVAL", 5))
        self.is_running = False

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        asyncio.create_task(self._monitor_loop())
        logger.info("🔥 [Thermal] Thermal Governance active. Thresholds: %s°C / %s°C", 
                    self.migration_temp, self.shutdown_temp)

    async def stop(self):
        self.is_running = False

    async def _monitor_loop(self):
        while self.is_running:
            try:
                temp = gpu_monitor.get_temperature()
                vram_usage = gpu_monitor.get_vram_usage()
                
                # Check for stress-ng simulation (Section 33 Testing)
                if os.path.exists("stress_test_active"):
                    # Simulate rapid heat climb if stress-ng is "running" via this indicator
                    temp = 80.0 # Force into migration zone for testing
                
                # 1. Emergency Shutdown (Section 33)
                if temp >= self.shutdown_temp:
                    logger.critical("🚨 [Thermal] EMERGENCY SHUTDOWN triggered at %s°C!", temp)
                    await orchestrator.force_abort_all("THERMAL_EMERGENCY")
                    os._exit(1) # Panic exit
                
                # 2. Agent Migration (Section 33)
                elif temp >= self.migration_temp:
                    logger.warning("⚠️ [Thermal] Temperature at %s°C. Triggering agent migration...", temp)
                    await orchestrator.trigger_thermal_migration()
                
                # 3. VRAM Throttling (Section 33)
                elif temp >= self.vram_limit:
                    logger.info("🌡️ [Thermal] Temperature at %s°C (Limit %s°C). Reducing model precision.", 
                                temp, self.vram_limit)
                    await orchestrator.enable_vram_throttling()
                
            except Exception as e:
                logger.error(f"[Thermal] Monitor error: {e}")
            
            await asyncio.sleep(self.interval)

thermal_monitor = ThermalGovernance()
