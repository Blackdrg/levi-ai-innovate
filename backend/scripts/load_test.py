
import asyncio
import time
import aiohttp
import logging
import statistics
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8000" # Target LEVI-AI endpoint
MISSION_ENDPOINT = f"{BASE_URL}/api/v1/missions"
CONCURRENT_USERS = 50 # Start with 50, escalate to 100
TOTAL_REQUESTS = 200
TIMEOUT = 60 # seconds

class LoadTester:
    def __init__(self):
        self.latencies: List[float] = []
        self.success_count = 0
        self.failure_count = 0

    async def run_mission(self, session: aiohttp.ClientSession, user_id: int):
        """Simulates a single user mission request."""
        payload = {
            "text": f"User {user_id} Load Test: Summarize the concept of Sovereign Intelligence.",
            "session_id": f"load_test_sess_{user_id}_{int(time.time())}"
        }
        
        start_time = time.time()
        try:
            async with session.post(MISSION_ENDPOINT, json=payload, timeout=TIMEOUT) as resp:
                if resp.status == 200:
                    self.success_count += 1
                    latency = (time.time() - start_time) * 1000
                    self.latencies.append(latency)
                else:
                    self.failure_count += 1
                    logger.error(f"Request failed for User {user_id}: HTTP {resp.status}")
        except Exception as e:
            self.failure_count += 1
            logger.error(f"Request anomaly for User {user_id}: {e}")

    async def run_test(self):
        """Orchestrates the concurrent load test."""
        logger.info(f"🚀 Starting Sovereign Load Test: {CONCURRENT_USERS} concurrent users, {TOTAL_REQUESTS} total requests.")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(TOTAL_REQUESTS):
                # Throttle concurrency
                if len(tasks) >= CONCURRENT_USERS:
                    done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
                tasks.append(asyncio.create_task(self.run_mission(session, i)))
            
            # Wait for remaining
            if tasks:
                await asyncio.wait(tasks)

        self.report()

    def report(self):
        """Generates the performance report."""
        logger.info("--- Sovereign Performance Report ---")
        logger.info(f"Total Requests: {TOTAL_REQUESTS}")
        logger.info(f"Successes: {self.success_count}")
        logger.info(f"Failures: {self.failure_count}")
        
        if self.latencies:
            logger.info(f"Avg Latency:  {statistics.mean(self.latencies):.2f}ms")
            logger.info(f"Min Latency:  {min(self.latencies):.2f}ms")
            logger.info(f"Max Latency:  {max(self.latencies):.2f}ms")
            if len(self.latencies) > 1:
                logger.info(f"P95 Latency:  {statistics.quantiles(self.latencies, n=20)[18]:.2f}ms")
        
        success_rate = (self.success_count / TOTAL_REQUESTS) * 100
        logger.info(f"Global Success Rate: {success_rate:.2f}%")
        
        if success_rate >= 95 and (self.latencies and statistics.mean(self.latencies) < 5000):
            logger.info("✅ PASS: System meets Sovereign Production Hardening standards (Phase 6).")
        else:
            logger.warning("⚠️ FAIL: System requires further optimization to meet Phase 6 mission-critical SLAs.")

if __name__ == "__main__":
    tester = LoadTester()
    asyncio.run(tester.run_test())
