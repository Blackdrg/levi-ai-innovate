import pytest
import asyncio
import httpx
from unittest.mock import patch

BASE = "http://localhost:8000"

@pytest.mark.asyncio
async def test_circuit_breaker_trips_on_redis_latency(async_client):
    """
    Sovereign Circuit Breaker Test.
    Simulate 6 consecutive Redis failures -> circuit opens -> 503.
    """
    client = async_client
    # 1. Authenticate
    auth = await client.post("/api/v1/auth/token",
        json={"username": "test_pro", "password": "test_pw"})
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Patch Redis Client with Latency Spike/Timeout
    # Note: The patch path should match where the orchestrator imports it.
    # In our v13, it imports from backend.db.redis
    with patch("backend.db.redis.r.get", side_effect=asyncio.TimeoutError):
        # 3. Consecutive Failures (Threshold is 5 in our redis_breaker)
        responses = []
        for i in range(7):
            res = await client.post("/api/v1/orchestrator/mission",
                json={"input": "Trip the circuit.", "context": {"tier": "L1"}},
                headers=headers)
            responses.append(res.status_code)
            await asyncio.sleep(0.1)
            
        # One of these must be 503 once the circuit opens
        assert any(s == 503 for s in responses), f"Circuit breaker failed to trip. Status codes: {responses}"
        
    # 4. Verify Recovery (Wait for recovery_time = 60s in production, but we can lower it for test)
    # For the sake of a fast integration test, we verify the OPEN state logic here.
    # Check polling status while circuit is OPEN
    with patch("backend.db.redis.r.get", side_effect=asyncio.TimeoutError):
        late_res = await client.get("/api/v1/orchestrator/mission/any", headers=headers)
        assert late_res.status_code == 503 # Should still be 503
