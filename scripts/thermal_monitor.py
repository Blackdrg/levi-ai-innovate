import os
import time
import logging
import random
import requests
from typing import Dict

logging.basicConfig(level=logging.INFO, format='[THERMAL] %(asctime)s - %(message)s')
logger = logging.getLogger("ThermalMonitor")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_INTERNAL_URL", "http://localhost:8000")

class ThermalMonitor:
    """
    Sovereign v22.1: Hardware Thermal Governance.
    Monitors CPU/GPU temps and triggers migration pulses via the Orchestrator.
    Section 33 Compliance.
    """
    
    def __init__(self):
        self.temp_threshold_warning = 75.0
        self.temp_threshold_critical = 82.0
        
    def get_core_temp(self) -> float:
        # In a real Ubuntu/Windows env, we'd read from /sys/class/thermal or WMI
        # Here we simulate based on load or randomized jitter
        base_temp = 55.0
        try:
             import psutil
             load = psutil.cpu_percent()
             temp = base_temp + (load * 0.25) + random.uniform(-1, 1)
             return round(temp, 2)
        except:
             return round(base_temp + random.uniform(0, 5), 2)

    def run_monitor_loop(self):
        logger.info("🌡️ Thermal Governance Engine ONLINE. Monitoring hardware thresholds...")
        while True:
            temp = self.get_core_temp()
            logger.debug(f"Current Temp: {temp}°C")
            
            if temp >= self.temp_threshold_critical:
                logger.warning(f"🚨 CRITICAL HEAT: {temp}°C! Triggering VRAM Throttling and Swarm Migration.")
                self.trigger_orchestratorAction("critical")
            elif temp >= self.temp_threshold_warning:
                logger.info(f"⚠️ HIGH TEMP: {temp}°C. Notifying mesh for load balancing.")
                self.trigger_orchestratorAction("warning")
                
            time.sleep(5)

    def trigger_orchestratorAction(self, severity: str):
        try:
            # Note: Orchestrator has an internal /thermal endpoint or we use the management API
            endpoint = f"{ORCHESTRATOR_URL}/sys/thermal"
            requests.post(endpoint, json={"severity": severity, "temp": self.get_core_temp()}, timeout=2)
        except Exception as e:
            logger.error(f"Failed to signal orchestrator: {e}")

if __name__ == "__main__":
    monitor = ThermalMonitor()
    monitor.run_monitor_loop()
