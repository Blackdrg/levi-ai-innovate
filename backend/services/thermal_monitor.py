# backend/services/thermal_monitor.py
import logging
import asyncio
import os
from backend.core.orchestrator import orchestrator

logger = logging.getLogger("Thermal")

class ThermalMonitor:
    """
    Sovereign v22.1: Server-side Thermal Governance.
    Section 33 Compliance.
    Handles signals from hardware monitors and coordinates swarm migration.
    """
    def __init__(self):
        self._task = None
        self.critical_threshold = 82.0
        self.warning_threshold = 75.0

    async def start(self):
        logger.info("🌡️ [Thermal] Monitoring service initialized.")
        # Background loop to check local metrics if scripts/thermal_monitor.py isn't used
        self._task = asyncio.create_task(self._self_check_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def handle_hardware_signal(self, severity: str, temp: float):
        """Called by the /sys/thermal API endpoint."""
        logger.warning(f"🌡️ [Thermal] Hardware Signal: {severity.upper()} (Temp: {temp}°C)")
        
        if severity == "critical":
            await orchestrator.enable_vram_throttling()
            await orchestrator.trigger_thermal_migration()
        elif severity == "warning":
            await orchestrator.migrate_agents_to_cooler_nodes()

    async def _self_check_loop(self):
        from backend.utils.hardware import gpu_monitor
        while True:
            try:
                temp = gpu_monitor.get_temperature()
                vram = gpu_monitor.get_vram_usage()
                
                # VRAM Throttling (90% Threshold)
                if vram.get("active") and vram["percent"] > 90.0:
                    logger.warning(f"🌡️ [Thermal] VRAM Pressure Critical: {vram['percent']:.1f}%")
                    await orchestrator.enable_vram_throttling()

                if temp >= self.critical_threshold:
                    await self.handle_hardware_signal("critical", temp)
                elif temp >= self.warning_threshold:
                    await self.handle_hardware_signal("warning", temp)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"[Thermal] Self-check failed: {e}")
                await asyncio.sleep(60)

thermal_monitor = ThermalMonitor()
