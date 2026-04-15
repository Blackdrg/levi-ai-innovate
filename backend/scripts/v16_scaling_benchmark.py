"""
LEVI-AI Scaling Benchmark v16.1.
Simulates high-throughput mission execution across the 4-Tier Memory and Distributed Cognitive Network.
Targets: 100,000 missions/min capacity.
"""

import asyncio
import time
import logging
from backend.core.orchestrator import _orchestrator as orchestrator

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("scaling_benchmark")

async def run_mission_burst(count=100):
    start = time.perf_counter()
    tasks = []
    
    for i in range(count):
        mission_input = f"Benchmarking mission {i}. Perform a cognitive sweep of the local hive status."
        tasks.append(orchestrator.handle_mission("benchmark_user", mission_input))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.perf_counter() - start
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    return duration, success_count

async def run_test():
    print("🚀 [Scaling] Initiating 100,000 Mission Capacity Audit...")
    
    # Warmup
    await run_mission_burst(5)
    
    total_missions = 500 # Scaled down for local validation, extrapolated and monitored
    batch_size = 50
    batches = total_missions // batch_size
    
    start_all = time.perf_counter()
    all_success = 0
    
    for i in range(batches):
        dur, succ = await run_mission_burst(batch_size)
        all_success += succ
        print(f"📦 Batch {i+1}/{batches} completed: {batch_size} missions in {dur:.2f}s")
        
    total_dur = time.perf_counter() - start_all
    throughput = (all_success / total_dur) * 60
    
    print(f"\n📊 --- SCALING REPORT ---")
    print(f"⏱️ Total Duration: {total_dur:.2f}s")
    print(f"✅ Successful Missions: {all_success}")
    print(f"🚀 Extrapolated Throughput: {throughput:,.2f} missions/minute")
    
    if throughput > 100000:
        print("🏆 STATUS: SCALE GRADUATED (100k Ready)")
    else:
        print("⚠️ STATUS: LIMIT REACHED (Check Resource Pressure / Redis T0)")

if __name__ == "__main__":
    asyncio.run(run_test())
