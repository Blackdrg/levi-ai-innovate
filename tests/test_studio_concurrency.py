import asyncio
import httpx
import time

BASE_URL = "http://localhost:8000"

async def trigger_gen(client, i):
    payload = {
        "text": f"Verification test message {i}",
        "author": "Tester",
        "mood": "philosophical"
    }
    print(f"[{i}] Sending request...")
    start = time.time()
    try:
        resp = await client.post(f"{BASE_URL}/generate_image", json=payload)
        duration = time.time() - start
        print(f"[{i}] Response: {resp.status_code} in {duration:.2f}s")
        if resp.status_code == 200:
            print(f"[{i}] Job ID: {resp.json().get('job_id')}")
    except Exception as e:
        print(f"[{i}] Error: {e}")

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # Launch 5 concurrent requests
        # With semaphore=3, we should see 3 start immediately and 2 wait?
        # Actually BackgroundTasks are handled after the response is sent, 
        # but the task execution itself will be limited by the semaphore.
        tasks = [trigger_gen(client, i) for i in range(5)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    print("Ensure the backend is running at http://localhost:8000")
    asyncio.run(main())
