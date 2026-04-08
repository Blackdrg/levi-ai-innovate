from __future__ import annotations

import pytest

from backend.utils.health import probe_dependencies
from backend.utils.startup import collect_default_secret_warnings


@pytest.mark.asyncio
async def test_probe_dependencies_reports_all_backends(monkeypatch):
    class FakeRedis:
        async def ping(self):
            return True

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "llama3.1:8b"}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            assert url.endswith("/api/tags")
            return FakeResponse()

    async def fake_verify_resonance():
        return True

    monkeypatch.setattr("backend.utils.health.HAS_REDIS_ASYNC", True)
    monkeypatch.setattr("backend.utils.health.r_async", FakeRedis())
    monkeypatch.setattr("backend.utils.health.verify_resonance", fake_verify_resonance)
    monkeypatch.setattr("backend.utils.health.httpx.AsyncClient", lambda timeout=5.0: FakeClient())

    result = await probe_dependencies()

    assert result["status"] == "online"
    assert result["checks"]["redis"]["ok"] is True
    assert result["checks"]["postgres"]["ok"] is True
    assert result["checks"]["ollama"]["ok"] is True
    assert "llama3.1:8b" in result["checks"]["ollama"]["models"]


def test_collect_default_secret_warnings_detects_placeholders(monkeypatch):
    monkeypatch.setenv("AUDIT_CHAIN_SECRET", "change-me")
    monkeypatch.setenv("ENCRYPTION_KEY", "kms_master_key")

    warnings = collect_default_secret_warnings()

    assert any("AUDIT_CHAIN_SECRET" in warning for warning in warnings)
    assert any("ENCRYPTION_KEY" in warning for warning in warnings)
