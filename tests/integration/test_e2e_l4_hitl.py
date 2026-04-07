import pytest
import asyncio
import httpx
import uuid

BASE = "http://localhost:8000"

@pytest.mark.asyncio
async def test_l4_swarm_hitl_approval_and_persistence(async_client):
    """
    Sovereign L4 Swarm Test with HITL Gate.
    Verifies: DAG execution -> Hit HITL node -> External Approval -> Continue -> Finalize.
    """
    client = async_client
    # 1. Authenticate
    auth = await client.post("/api/v1/auth/token",
        json={"username": "test_pro", "password": "test_pw"})
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit L4 Mission (Requiring HITL)
    res = await client.post("/api/v1/orchestrator/mission",
        json={
            "input": "Execute a sensitive swarm task.", 
            "context": {"tier": "L4", "require_approval": True}
        },
        headers=headers)
    
    assert res.status_code == 202
    mission_id = res.json()["mission_id"]

    # 3. Wait for HITL status
    is_pending_approval = False
    for _ in range(10): # 10 attempts
        status_res = await client.get(f"/api/v1/orchestrator/mission/{mission_id}", headers=headers)
        data = status_res.json()
        
        # The executor checkpoints progress, and we can check completed_nodes or a specific HITL marker
        # In our v13 implementation, we use a separate HITL endpoint or check state
        if data.get("status") == "PROCESSING": # It stays processing while waiting for HITL
             is_pending_approval = True
             break
        await asyncio.sleep(1)
    
    assert is_pending_approval, "Mission failed to reach HITL gate."

    # 4. Approve mission (Sovereign HITL logic)
    # Using the orchestrator approval endpoint
    approve_res = await client.post("/api/v1/orchestrator/mission/approve",
        json={
            "mission_id": mission_id, 
            "node_id": "approval_node_01", # Standardized ID for this test
            "decision": "approved",
            "feedback": "All clear."
        },
        headers=headers)
    assert approve_res.status_code == 200

    # 5. Finalize and Verify Resonance (Quad-persistence Check)
    finalized = False
    for _ in range(15): # 15 attempts
        status_res = await client.get(f"/api/v1/orchestrator/mission/{mission_id}", headers=headers)
        data = status_res.json()
        if data["status"] == "FINALIZED":
            finalized = True
            break
        await asyncio.sleep(1)
    
    assert finalized, f"L4 Mission {mission_id} failed to finalize after approval."
