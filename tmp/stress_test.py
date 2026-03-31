import asyncio
import time
import logging
import uuid
from typing import List, Dict, Any
from backend.services.orchestrator.brain import LeviBrain

# Configure logging for stress test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StressTest")

async def simulate_request(brain: LeviBrain, user_id: str, request_idx: int):
    """Simulates a single user request to the orchestrator."""
    start = time.time()
    try:
        # We use a synthetic input to trigger different paths
        user_input = f"Hello LEVI! This is test request #{request_idx}"
        
        # Call the orchestrator (Mocking or real depending on env)
        result = await brain.route(
            user_input=user_input,
            user_id=user_id,
            session_id=f"stress_session_{user_id}",
            mood="philosophical",
            user_tier="free"
        )
        
        duration = (time.time() - start) * 1000
        status = "HIT" if result.get("route") == "cache" else "MISS"
        logger.info(f"[Req {request_idx}] Duration: {int(duration)}ms | Route: {result.get('route')} | Cache: {status}")
        return True
    except Exception as e:
        duration = (time.time() - start) * 1000
        logger.error(f"[Req {request_idx}] FAILED after {int(duration)}ms: {e}")
        return False

async def run_stress_test(concurrency: int = 50):
    """Dispatches multiple parallel requests to the Brain."""
    print(f"\n--- 🚀 Starting Stress Test (Concurrency: {concurrency}) ---")
    brain = LeviBrain()
    user_id = f"tester_{uuid.uuid4().hex[:4]}"
    
    start_time = time.time()
    
    # asyncio.gather dispatches all tasks in parallel
    tasks = [simulate_request(brain, user_id, i) for i in range(concurrency)]
    results = await asyncio.gather(*tasks)
    
    total_duration = time.time() - start_time
    success_count = sum(1 for r in results if r)
    fail_count = len(results) - success_count
    
    print("\n--- 📊 Stress Test Results ---")
    print(f"Total Requests: {len(results)}")
    print(f"Successes:      {success_count}")
    print(f"Failures:       {fail_count}")
    print(f"Total Time:     {total_duration:.2f}s")
    print(f"Avg Throughput: {len(results) / total_duration:.2f} req/s")
    
    # Check Circuit Breaker State (from Redis stats)
    from backend.redis_client import r as redis_client, HAS_REDIS
    if HAS_REDIS:
        api_fails = int(redis_client.get("stats:failures:chat_agent") or 0)
        print(f"Stored Agent Failures (Today): {api_fails}")
        if api_fails > 0:
            print("⚠️ Note: Some agent failures were recorded. The Circuit Breaker may have been engaged.")

if __name__ == "__main__":
    asyncio.run(run_stress_test(50))
