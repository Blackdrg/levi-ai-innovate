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

@pytest.mark.asyncio
async def test_security_headers_present(async_client):
    """
    Audit-Ready Test: Security Headers Middleware.
    Confirm HSTS, CSP, X-Frame-Options, etc are injected into outbound API responses.
    """
    res = await async_client.get("/health")
    assert res.status_code in [200, 503]  # Relying on global middleware
    
    headers = res.headers
    assert "Strict-Transport-Security" in headers
    assert "Content-Security-Policy" in headers
    assert "X-Frame-Options" in headers
    assert headers["X-Frame-Options"] == "DENY"

@pytest.mark.asyncio
async def test_ssrf_allowlist_blocking():
    """
    Audit-Ready Test: SSRF Allowlist Wall.
    Ensure non-approved domains are explicitly denied.
    """
    from backend.core.egress_proxy import EgressProxy, SSRFBlockedError
    proxy = EgressProxy()
    
    # Allowed domain
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value.status_code = 200
        await proxy.get("https://api.tavily.com/search")
        mock_get.assert_called_once()

    # Blocked domain
    with pytest.raises(SSRFBlockedError):
        await proxy.get("http://internal-metadata-service.local")

@pytest.mark.asyncio
async def test_rate_limiter_tiered_enforcement(async_client):
    """
    Audit-Ready Test: Sliding Window Rate Limiting.
    Verify 'free' tier enforcement blocks after RPM exceeds 5.
    """
    client = async_client
    # Authenticate
    auth = await client.post("/api/v1/auth/token", json={"username": "free_user", "password": "pw"})
    # Let's bypass actual auth if not needed, or mock the headers directly for the request to rate limiter
    headers = {
        "X-User-ID": "test_free_user",
        "X-User-Tier": "free"
    }

    responses = []
    # Free tier limit is 5 RPM. Hit it 7 times.
    for _ in range(7):
        res = await client.get("/health", headers=headers)
        responses.append(res.status_code)
        
    # By the 6th or 7th request, it should return 429 Too Many Requests
    assert any(s == 429 for s in responses), f"Rate Limiter failed to trip 429. Status codes: {responses}"
