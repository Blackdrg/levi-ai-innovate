import pytest
import asyncio
import httpx
import uuid

BASE = "http://localhost:8000"

@pytest.mark.asyncio
async def test_l1_chat_mission_roundtrip(async_client):
    """
    Sovereign L1 Mission Smoke Test.
    HTTP in -> RBAC -> Brain -> Async Processing -> Poll -> Result.
    """
    client = async_client
    # 1. Authenticate (using the mock token flow)
    auth = await client.post("/api/v1/auth/token",
        json={"username": "test_pro", "password": "test_pw"})
    assert auth.status_code == 200
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit mission (L1 query)
    res = await client.post("/api/v1/orchestrator/mission",
        json={"input": "What is 2+2?", "context": {"tier": "L1"}},
        headers=headers)
    
    assert res.status_code == 202
    mission_id = res.json()["mission_id"]
    assert mission_id.startswith("mission_")

    # 3. Poll for result (Wait for FINALIZED status)
    success = False
    for _ in range(10): # 10 attempts, 1 sec each
        status_res = await client.get(f"/api/v1/orchestrator/mission/{mission_id}", headers=headers)
        assert status_res.status_code == 200
        data = status_res.json()
        
        if data["status"] == "FINALIZED":
            assert "4" in str(data["result"])
            assert data["fidelity_score"] >= 0.9
            success = True
            break
        
        await asyncio.sleep(1)
    
    assert success, f"Mission {mission_id} failed to finalize in time."
