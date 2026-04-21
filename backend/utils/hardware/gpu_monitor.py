import logging
import os
try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False

logger = logging.getLogger("gpu-monitor")

class GpuMonitor:
    """
    Sovereign OS v22.1: Production-grade GPU VRAM & Thermal Gauge.
    Uses NVML (pynvml) for real-time hardware telemetry on DRIVE D.
    """
    def __init__(self):
        self.active = False
        if HAS_PYNVML:
            try:
                pynvml.nvmlInit()
                self.active = True
                self.device_count = pynvml.nvmlDeviceGetCount()
                logger.info(f"📊 [GPU] NVML Initialized. Found {self.device_count} accelerator(s).")
            except Exception as e:
                logger.warning(f"📊 [GPU] NVML Initialization failed: {e}")
        else:
            logger.warning("📊 [GPU] pynvml not installed. Running in simulation mode (Zero-Telemetry).")

    def get_vram_usage(self) -> dict:
        """
        Polls VRAM usage across all detectable devices.
        Returns aggregate available capacity in GB.
        """
        if not self.active:
            return {"active": False, "available": 0.0, "total": 0.0}

        try:
            total_available = 0.0
            total_capacity = 0.0
            for i in range(self.device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_available += info.free / (1024**3)
                total_capacity += info.total / (1024**3)
            
            return {
                "active": True,
                "available": total_available,
                "total": total_capacity,
                "utilization": 1.0 - (total_available / total_capacity) if total_capacity > 0 else 0
            }
        except Exception as e:
            logger.error(f"📊 [GPU] VRAM polling error: {e}")
            return {"active": False, "available": 0.0}

    def get_thermal_metrics(self) -> list:
        """
        Polls core temperatures for the ThermalGauge.
        """
        if not self.active:
            return []

        thermals = []
        try:
            for i in range(self.device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                thermals.append({"device": i, "temp_c": temp})
            return thermals
        except Exception as e:
            logger.error(f"📊 [GPU] Thermal polling error: {e}")
            return []

    def __del__(self):
        if self.active:
            try:
                pynvml.nvmlShutdown()
            except: pass

gpu_monitor = GpuMonitor()
