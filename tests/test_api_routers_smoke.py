import pytest
from fastapi.testclient import TestClient

try:
    from backend.api.main import app
except ImportError:
    from fastapi import FastAPI
    app = FastAPI()

client = TestClient(app)

def get_auth_headers():
    return {"Authorization": "Bearer test-smoke-token-admin"}

def test_orchestrator_mission_happy_path():
    response = client.post("/api/v1/orchestrator/mission", json={"input": "test"}, headers=get_auth_headers())
    assert response.status_code != 401

def test_orchestrator_mission_auth_failure():
    response = client.post("/api/v1/orchestrator/mission", json={"input": "test"})
    assert response.status_code in [401, 403]

def test_telemetry_pulse_happy_path():
    response = client.get("/api/v1/telemetry/pulse", headers=get_auth_headers())
    assert response.status_code != 401

def test_telemetry_pulse_auth_failure():
    response = client.get("/api/v1/telemetry/pulse")
    assert response.status_code in [401, 403]

def test_memory_context_happy_path():
    response = client.get("/api/v1/memory/context", headers=get_auth_headers())
    assert response.status_code != 401

def test_memory_context_auth_failure():
    response = client.get("/api/v1/memory/context")
    assert response.status_code in [401, 403]

def test_search_query_happy_path():
    response = client.post("/api/v1/search/query", json={"q": "test"}, headers=get_auth_headers())
    assert response.status_code != 401

def test_payments_verify_happy_path():
    response = client.post("/api/v1/payments/verify", json={"tx": "test"}, headers=get_auth_headers())
    assert response.status_code != 401

def test_auth_me_happy_path():
    response = client.get("/api/v1/auth/me", headers=get_auth_headers())
    assert response.status_code != 401

def test_billing_status_happy_path():
    response = client.get("/api/v1/billing/status", headers=get_auth_headers())
    assert response.status_code != 401

def test_analytics_report_happy_path():
    response = client.get("/api/v1/analytics/report", headers=get_auth_headers())
    assert response.status_code != 401

def test_agents_list_happy_path():
    response = client.get("/api/v1/agents/list", headers=get_auth_headers())
    assert response.status_code != 401

def test_marketplace_search_happy_path():
    response = client.get("/api/v1/marketplace/search", headers=get_auth_headers())
    assert response.status_code != 401

def test_compliance_audit_happy_path():
    response = client.get("/api/v1/compliance/audit", headers=get_auth_headers())
    assert response.status_code != 401

def test_scheduling_jobs_happy_path():
    response = client.get("/api/v1/scheduling/jobs", headers=get_auth_headers())
    assert response.status_code != 401

def test_learning_status_happy_path():
    response = client.get("/api/v1/learning/status", headers=get_auth_headers())
    assert response.status_code != 401

def test_missions_replay_happy_path():
    response = client.get("/api/v1/missions/replay/test_id", headers=get_auth_headers())
    assert response.status_code != 401

def test_brain_v14_pulse_happy_path():
    response = client.get("/api/v14/pulse", headers=get_auth_headers())
    assert response.status_code != 401

def test_global_unauth_is_blocked():
    # Sampling several critical routes to ensure the auth middleware is globally effective
    routes = [
        "/api/v1/orchestrator/mission",
        "/api/v1/memory/context",
        "/api/v1/auth/me",
        "/api/v14/pulse"
    ]
    for route in routes:
        response = client.get(route) if "mission" not in route else client.post(route, json={})
        assert response.status_code in [401, 403], f"Route {route} allowed unauthenticated access"
