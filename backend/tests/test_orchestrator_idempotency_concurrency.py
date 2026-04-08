from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("TEST_MODE", "true")

from backend.core.orchestrator import Orchestrator


class _FakeRedis:
    def __init__(self):
        self.data = {}
        self.lock = asyncio.Lock()

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value
        return True

    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
        return self.data[key]

    def expire(self, key, ttl):
        return True

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True


@pytest.mark.asyncio
async def test_identical_missions_only_execute_once(monkeypatch):
    redis = _FakeRedis()
    executions = 0

    async def fake_run(*args, **kwargs):
        nonlocal executions
        executions += 1
        await asyncio.sleep(0.05)
        return {"response": "ok", "results": []}

    monkeypatch.setattr("backend.core.execution_state.HAS_REDIS", True)
    monkeypatch.setattr("backend.core.execution_state.redis_client", redis)
    monkeypatch.setattr("backend.core.orchestrator.check_exact_match", lambda *args, **kwargs: None)
    monkeypatch.setattr("backend.core.orchestrator.check_semantic_match", lambda *args, **kwargs: None)
    monkeypatch.setattr("backend.core.orchestrator.store_exact_match", lambda *args, **kwargs: None)

    orchestrator = Orchestrator()
    orchestrator.brain.run = fake_run
    orchestrator.is_soft_deleted = lambda user_id: asyncio.sleep(0, result=False)
    orchestrator.check_rate_limit = lambda user_id, tier: asyncio.sleep(0, result=(False, {}))

    tasks = [
        orchestrator.handle_mission(
            user_input="same mission",
            user_id="user-1",
            session_id="session-1",
            idempotency_key="shared-key",
        )
        for _ in range(12)
    ]
    results = await asyncio.gather(*tasks)

    assert executions == 1
    duplicates = [result for result in results if result.get("status") == "duplicate"]
    successes = [result for result in results if result.get("response") == "ok"]
    assert len(successes) == 1
    assert len(duplicates) == 11
