import os
import time
import subprocess
import json
import logging
import asyncio
from backend.db.redis import r_async as redis_client

logger = logging.getLogger(__name__)

async def get_vram_usage():
    """
    Queries nvidia-smi for VRAM telemetry.
    Returns free VRAM in MB.
    """
    try:
        # Querying free memory in MB
        result = await asyncio.to_thread(
            subprocess.check_output,
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,nounit,noheader"],
            encoding="utf-8"
        )
        free_mb = int(result.strip().split("\n")[0])
        return free_mb
    except Exception as e:
        logger.error(f"[VRAM Monitor] Failed to query nvidia-smi: {e}")
        return None

async def vram_monitor_loop():
    """
    Background loop that publishes VRAM status to Redis every 5s.
    """
    logger.info("[VRAM Monitor] Starting Sovereign VRAM Telemetry...")
    while True:
        try:
            free_mb = await get_vram_usage()
            if free_mb is not None:
                # Publish to Redis
                await redis_client.set("vram:live", free_mb, ex=10)
                
                # Check for pressure (threshold < 3000MB)
                pressure = "true" if free_mb < 3000 else "false"
                await redis_client.set("vram:pressure", pressure, ex=10)
                
                if pressure == "true":
                    logger.warning(f"[VRAM Monitor] CRITICAL: VRAM Pressure detected! Free: {free_mb}MB")
            
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"[VRAM Monitor] Loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # For standalone testing
    asyncio.run(vram_monitor_loop())
