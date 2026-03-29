from fastapi.testclient import TestClient # type: ignore
from backend.gateway import app
import pytest # type: ignore

client = TestClient(app)

def test_gateway_root():
    """Verify that the gateway root is accessible."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "LEVI Gateway"

def test_gateway_health():
    """Verify the production-grade health check logic."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data

def test_gateway_auth_mount(app_client):
    """Verify that auth router is correctly mounted on the gateway."""
    # Test a route that should be in the auth router
    response = app_client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password"})
    assert response.status_code != 404

def test_gateway_chat_mount():
    """Ensure Chat router is correctly mounted."""
    response = client.post("/api/v1/chat", json={"message": "ping"})
    assert response.status_code != 404
