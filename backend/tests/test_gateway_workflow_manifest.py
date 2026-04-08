from fastapi.testclient import TestClient

from backend.main import app
from backend.api.utils.auth import get_current_user


def test_workflow_manifest_endpoint_exposes_designated_pipeline():
    app.dependency_overrides[get_current_user] = lambda: {"uid": "test-user"}
    client = TestClient(app)
    try:
        response = client.get("/api/v1/telemetry/workflow")
    finally:
        app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "connected"
    assert payload["workflow"]["healthy"] is True
    assert payload["workflow"]["stages"][0] == "gateway"
    assert "node_latency_ms" in payload["contracts"]["core_metrics"]


def test_gateway_sets_trace_headers():
    client = TestClient(app)
    response = client.get("/health", headers={"X-Trace-ID": "trace-test-123"})
    assert response.status_code == 200
    assert response.headers["X-Trace-ID"] == "trace-test-123"
    assert "X-Sovereign-Version" in response.headers
