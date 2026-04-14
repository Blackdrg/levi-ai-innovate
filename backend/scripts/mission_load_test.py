import asyncio
import time
import logging
import random
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.orchestrator import Orchestrator
from backend.core.orchestrator_types import BrainMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LoadTester")

CONCURRENCY = 10
TOTAL_MISSIONS = 30

async def runner(orchestrator, mission_id):
    inputs = [
        "Synthesize a python script for deep learning.",
        "Search for latest news on autonomous agents.",
        "Analyze the connection between Stoicism and modern AI.",
        "Explain the Raft consensus algorithm with diagrams.",
        "Research the impact of DCN on global latency."
    ]
    user_input = random.choice(inputs)
    start_time = time.time()
    
    logger.info(f"🚀 Mission {mission_id} START: {user_input[:40]}...")
    try:
        # We invoke handle_mission logic (mocking the API call)
        # Note: In a real test, we'd use the HTTP endpoint, but for internal engine validation,
        # calling the orchestrator directly is more high-fidelity for core logic testing.
        result = await orchestrator.handle_mission(
            user_input=user_input,
            user_id="load_test_user",
            session_id=f"sess_{mission_id}"
        )
        latency = (time.time() - start_time) * 1000
        logger.info(f"✅ Mission {mission_id} COMPLETE ({latency:.2f}ms). Outcome status: {result.get('route')}")
        return latency
    except Exception as e:
        logger.error(f"❌ Mission {mission_id} FAILED: {e}")
        return None

async def run_load_test():
    logger.info(f"🔥 [LoadTester] Initializing High-Fidelity Stress Test (Concurrency: {CONCURRENCY}, Total: {TOTAL_MISSIONS})")
    
    orchestrator = Orchestrator()
    # Ensure background engines are quiet for base-test or active if we want to measure interference
    # In GA, we want everything active.
    
    start_all = time.time()
    latencies = []
    
    sem = asyncio.Semaphore(CONCURRENCY)
    
    async def task_with_sem(i):
        async with sem:
            return await runner(orchestrator, f"m_load_{i}")

    tasks = [task_with_sem(i) for i in range(TOTAL_MISSIONS)]
    results = await asyncio.gather(*tasks)
    
    latencies = [r for r in results if r is not None]
    
    total_time = time.time() - start_all
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    throughput = len(latencies) / total_time
    
    logger.info("--- LOAD TEST RESULTS ---")
    logger.info(f"Total Time:     {total_time:.2f}s")
    logger.info(f"Throughput:     {throughput:.2f} Missions/sec")
    logger.info(f"Avg Latency:    {avg_latency:.2f}ms")
    logger.info(f"Success Rate:   {len(latencies)}/{TOTAL_MISSIONS}")
    
    if len(latencies) < TOTAL_MISSIONS * 0.9:
        logger.error("💥 [LoadTester] FAILURE: Success rate below 90% threshold.")
        sys.exit(1)
        
    logger.info("✨ [LoadTester] High-Fidelity Stress Test PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_load_test())
