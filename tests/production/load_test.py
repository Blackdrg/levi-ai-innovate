import sys
import os
import asyncio
import time
import logging
import uuid

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LoadTest")

async def run_mission_burst(orchestrator, count):
    """Fires off a burst of missions and measures throughput."""
    tasks = []
    user_id = "load_tester"
    
    start_time = time.time()
    for i in range(count):
        session_id = f"load_{uuid.uuid4().hex[:8]}"
        tasks.append(orchestrator.run_mission("Quick health check mission", user_id, session_id))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start_time
    
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    
    return {
        "count": count,
        "success": success_count,
        "duration": duration,
        "throughput_per_sec": count / duration
    }

async def main():
    """
    Phase 4.4: Load Testing.
    Target: 10,000 missions/minute (~166/sec).
    """
    orchestrator = Orchestrator()
    # In a real test, we would hit multiple nodes.
    # Here we measure local orchestrator throughput.
    
    logger.info("🚀 [LoadTest] Starting Phase 4.4 Benchmarking...")
    
    # Warm up
    await run_mission_burst(orchestrator, 5)
    
    # Test Burst
    burst_size = 50
    stats = await run_mission_burst(orchestrator, burst_size)
    
    logger.info(f"📊 [LoadTest] Burst Size: {stats['count']}")
    logger.info(f"📊 [LoadTest] Successful: {stats['success']}")
    logger.info(f"📊 [LoadTest] Duration: {stats['duration']:.2f}s")
    logger.info(f"📊 [LoadTest] Throughput: {stats['throughput_per_sec']:.2f} missions/sec")
    
    target_tps = 166.6
    if stats['throughput_per_sec'] >= target_tps:
        logger.info("🏆 [LoadTest] PERFORMANCE SLA: PASSED")
    else:
        logger.warning(f"⚠️ [LoadTest] PERFORMANCE SLA: BELOW TARGET (Target: {target_tps}/sec)")

if __name__ == "__main__":
    asyncio.run(main())
