import asyncio
import aiohttp
import time
import json
import statistics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("load-tester")

URL = "http://localhost:8000/api/v1/orchestrator/mission"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test-token"
}

print(f"Targeting {URL} ...")

async def make_request(session, req_id):
    payload = {
        "input": "Hello FAST mode, what is the current protocol status?",
        "session_id": f"python-load-{req_id}"
    }
    start = time.time()
    try:
        async with session.post(URL, json=payload, headers=HEADERS) as response:
            await response.read()
            duration = time.time() - start
            return duration, response.status
    except Exception as e:
        logger.error(f"Req {req_id} failed: {e}")
        return time.time() - start, 500

async def main():
    target_concurrent = 200
    total_requests = 1000
    
    print(f"Starting python load test: {total_requests} requests at concurrency {target_concurrent}...")
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(target_concurrent)
        
        async def sem_task(req_id):
            async with semaphore:
                return await make_request(session, req_id)
                
        tasks = [sem_task(i) for i in range(total_requests)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        durations = [r[0] for r in results]
        statuses = [r[1] for r in results]
        
        avg_time = statistics.mean(durations)
        p95_time = statistics.quantiles(durations, n=100)[94] if durations else 0
        success_rate = (statuses.count(200) / total_requests) * 100
        
        print("\n=== LOAD TEST RESULTS ===")
        print(f"Total Requests: {total_requests}")
        print(f"Concurrency:    {target_concurrent}")
        print(f"Success Rate:   {success_rate:.1f}%")
        print(f"Total Time:     {total_time:.2f}s")
        print(f"Avg Latency:    {avg_time:.3f}s")
        print(f"p95 Latency:    {p95_time:.3f}s")
        
        if p95_time < 3.0:
            print("\n✅ SUCCESS: P95 Latency is under the 3s FAST Mode SLO!")
        else:
            print("\n❌ FAILED: P95 Latency exceeds the 3s FAST Mode SLO.")

if __name__ == "__main__":
    asyncio.run(main())
