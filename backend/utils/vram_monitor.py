import logging
import asyncio
from backend.db.redis import r_async as redis_client
from backend.utils.metrics import MetricsHub
from backend.utils.hardware import gpu_monitor

logger = logging.getLogger(__name__)

async def vram_monitor_loop():
    """
    Background loop that publishes VRAM status to Redis every 5s.
    Sovereign v15.0: Uses NVML-backed GPUMonitor.
    """
    logger.info("[VRAM Monitor] Starting Sovereign VRAM Telemetry...")
    while True:
        try:
            usage = gpu_monitor.get_vram_usage()
            
            if usage.get("active"):
                # Publish to Redis (available VRAM in MB for legacy compat)
                free_mb = int(usage["available"] * 1024)
                await redis_client.set("vram:live", free_mb, ex=10)
                
                # Check for pressure (threshold < 20% available or < 3GB)
                pressure = "true" if (usage["percent"] > 85 or usage["available"] < 3.0) else "false"
                await redis_client.set("vram:pressure", pressure, ex=10)
                MetricsHub.set_backpressure("vram", pressure == "true")
                
                if pressure == "true":
                    logger.warning(f"[VRAM Monitor] CRITICAL: VRAM Pressure! Used: {usage['percent']:.1f}% Free: {usage['available']:.1f}GB")
            
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"[VRAM Monitor] Loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(vram_monitor_loop())
