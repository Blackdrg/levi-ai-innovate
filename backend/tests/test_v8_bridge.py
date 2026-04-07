import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.memory.cache import MemoryCache
from backend.api.v8.telemetry import _MISSION_SUBSCRIBERS, broadcast_mission_event

client = TestClient(app)

def test_mobile_pairing_flow():
    """
    Tests the Sovereign Link pairing flow:
    1. Generate token.
    2. Confirm link.
    3. Verify persistent link.
    """
    # 1. Generate Link Token (Mocking Auth)
    # Note: We skip the actual JWT check for this internal test if possible,
    # or we mock the dependency.
    user_id = "test_user_bridge"
    
    # Manually inject token into cache for testing confirmLink
    token = "test_pairing_token_123"
    MemoryCache.set(f"sovereign_link:{token}", user_id, expire=300)
    
    # 2. Confirm Link from Mobile
    response = client.post(f"/api/v8/mobile/link/confirm?token={token}&device_name=TestiPhone")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "linked"
    assert data["user_id"] == user_id
    assert data["device_name"] == "TestiPhone"
    
    # 3. Verify Token Invalidation
    assert MemoryCache.get(f"sovereign_link:{token}") is None
    
    # 4. Verify Persistent Link
    assert MemoryCache.get(f"linked_device:{user_id}") == "TestiPhone"

@pytest.mark.asyncio
async def test_telemetry_broadcast():
    """
    Tests the asynchronous telemetry broadcast logic.
    """
    user_id = "test_user_telemetry"
    queue = asyncio.Queue()
    
    # 1. Subscribe manually
    if user_id not in _MISSION_SUBSCRIBERS:
        _MISSION_SUBSCRIBERS[user_id] = []
    _MISSION_SUBSCRIBERS[user_id].append(queue)
    
    # 2. Broadcast event
    event_data = {"id": "t_core", "status": "active"}
    broadcast_mission_event(user_id, "mission_start", event_data)
    
    # 3. Verify Queue capture
    event = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert event["type"] == "mission_start"
    assert event["payload"] == event_data
    
    # Cleanup
    _MISSION_SUBSCRIBERS[user_id].remove(queue)

if __name__ == "__main__":
    test_mobile_pairing_flow()
    asyncio.run(test_telemetry_broadcast())
    print("Mobile Bridge Backend Tests Passed.")
