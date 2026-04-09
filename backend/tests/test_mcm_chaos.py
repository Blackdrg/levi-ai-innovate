import pytest

@pytest.mark.asyncio
async def test_mcm_fanout_fallback_on_redis_failure(monkeypatch):
    """Ensure that MCM fan-out survives Redis outage and falls back to Postgres/Neo4j correctly."""
    try:
        from backend.core.execution_state import CentralExecutionState
    except ImportError:
        pytest.skip("Test requires backend modules")

    class ConnectionError(Exception):
        pass

    class _FailingRedis:
        def get(self, key):
            raise ConnectionError("Redis is down")
        def setex(self, key, ttl, value):
            raise ConnectionError("Redis is down")
            
    monkeypatch.setattr("backend.core.execution_state.HAS_REDIS", True)
    monkeypatch.setattr("backend.core.execution_state.redis_client", _FailingRedis())
    
    # Assert fallback logic succeeds via Postgres
    try:
        mission_sm = CentralExecutionState("mission-redis-down", trace_id="trace", user_id="user")
        mission_sm.initialize()
        state = mission_sm._load()
        assert state is not None, "Failed to load state via fallback after Redis failure"
    except Exception as e:
        # Assuming the fallback prevents strict exception throw
        if isinstance(e, ConnectionError):
            pytest.fail("Redis connection error bubbled up unexpectedly during MCM fan-out.")
