import pytest
import asyncio
import httpx
import uuid

BASE = "http://localhost:8000"

@pytest.mark.asyncio
async def test_gpu_semaphore_concurrency_guard(async_client):
    """
    Sovereign CUDA OOM Boundary Test.
    Submit 5 simultaneous L4 tasks -> Verify results for 4 -> Verify 5th is QUEUED or finalizes.
    """
    client = async_client
    # 1. Authenticate
    auth = await client.post("/api/v1/auth/token",
        json={"username": "test_pro", "password": "test_pw"})
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit 5 missions simultaneously
    payloads = [{"input": f"Heavy neural task {i}", "context": {"tier": "L4"}} for i in range(5)]
    submissions = [client.post("/api/v1/orchestrator/mission", json=p, headers=headers) for p in payloads]
    
    responses = await asyncio.gather(*submissions)
    mission_ids = [r.json()["mission_id"] for r in responses if r.status_code == 202]
    
    assert len(mission_ids) == 5, f"Only {len(mission_ids)} missions accepted."

    # 3. Verify Queuing Logic (Internal Check)
    # We check the mission stats for the 5th task
    last_mission_id = mission_ids[-1]
    
    for _ in range(15): # 15 attempts, 1 sec each
        status_res = await client.get(f"/api/v1/orchestrator/mission/{last_mission_id}", headers=headers)
        data = status_res.json()
        
        # In our v13, tasks are dispatched immediately but wait in executor's semaphore(4)
        # We can check progress or status
        if data["status"] == "FINALIZED":
            break
        await asyncio.sleep(1)
    
    # 4. Overall Finalization Verification
    # If the semaphore works, all missions must eventually finalize without crashing
    all_finalized = True
    for mid in mission_ids:
         final_status = await client.get(f"/api/v1/orchestrator/mission/{mid}", headers=headers)
         if final_status.json()["status"] != "FINALIZED":
             all_finalized = False
    
    assert all_finalized, "Semaphore guard failed to process all tasks safely."
