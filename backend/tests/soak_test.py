import asyncio
import httpx
import psutil
import time
import random
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] soak_test: %(message)s")
logger = logging.getLogger("SOAK_TEST")

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")
NUM_MISSIONS = 500
SOAK_DURATION_HRS = 24
MISSION_INTERVAL_SEC = (SOAK_DURATION_HRS * 3600) / NUM_MISSIONS # Frequency to hit 500 missions in 24h

RANDOM_PROMPTS = [
    "Analyze system logs for security anomalies.",
    "Draft a mission plan for vectorizing global memory.",
    "Verify the DCN Raft consensus integrity.",
    "Simulate a thermal migration event and report.",
    "Optimize Neo4j relationship pruning strategy.",
    "Audit the serial bridge heartbeat for silence.",
    "Crystallize the learning pattern for mission-88."
]

async def dispatch_mission(client, iteration):
    prompt = random.choice(RANDOM_PROMPTS)
    logger.info(f"🚀 [{iteration}/{NUM_MISSIONS}] Dispatching mission: {prompt[:30]}...")
    try:
        start = time.perf_counter()
        resp = await client.post(f"{API_URL}/missions", json={
            "user_input": prompt,
            "user_id": f"soak_tester_{iteration % 10}",
            "session_id": f"soak_session_{iteration}"
        }, timeout=60.0)
        latency = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            logger.info(f"✅ Success. Latency: {latency:.2f}ms")
            return True, latency
        else:
            logger.error(f"❌ Failed: {resp.status_code} - {resp.text}")
            return False, latency
    except Exception as e:
        logger.error(f"💥 Crash: {e}")
        return False, 0

async def run_soak_test():
    logger.info(f"🛡️  LEVI-AI SOVEREIGN SOAK TEST STARTING...")
    logger.info(f"📊 Target: {NUM_MISSIONS} missions over {SOAK_DURATION_HRS} hours.")
    
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024**2 # MB
    
    stats = {"success": 0, "fail": 0, "latencies": []}
    
    async with httpx.AsyncClient() as client:
        for i in range(1, NUM_MISSIONS + 1):
            success, latency = await dispatch_mission(client, i)
            if success:
                stats["success"] += 1
                stats["latencies"].append(latency)
            else:
                stats["fail"] += 1
            
            # Monitoring Memory Growth
            current_mem = process.memory_info().rss / 1024**2
            growth = current_mem - start_memory
            logger.info(f"📈 Memory Usage: {current_mem:.2f}MB (Growth: {growth:.2f}MB)")
            
            if growth > 100 * (i * MISSION_INTERVAL_SEC / 3600): # 100MB/hr limit
                logger.critical(f"🚨 [LEAK ALERT] Memory growth exceeding 100MB/hr limit!")
            
            await asyncio.sleep(MISSION_INTERVAL_SEC)

    logger.info("🏁 SOAK TEST COMPLETE.")
    p50 = sorted(stats["latencies"])[len(stats["latencies"])//2] if stats["latencies"] else 0
    logger.info(f"📊 Results: Success={stats['success']}, Fail={stats['fail']}, p50_latency={p50:.2f}ms")

if __name__ == "__main__":
    try:
        asyncio.run(run_soak_test())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
