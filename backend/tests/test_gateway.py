from fastapi.testclient import TestClient # type: ignore
from backend.gateway import app
import pytest # type: ignore

client = TestClient(app)

def test_gateway_root():
    """Verify that the gateway root is accessible."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json()["service"] == "LEVI Gateway"

def test_gateway_health():
    """Verify the production-grade health check logic."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data

def test_gateway_auth_mount():
    """Ensure Auth router is correctly mounted under /api/v1."""
    # This should fail with 401/405 depending on the route, 
    # but 404 means it's not even mounted.
    response = client.post("/api/v1/login", json={"username": "test", "password": "123"})
    assert response.status_code != 404

def test_gateway_chat_mount():
    """Ensure Chat router is correctly mounted."""
    response = client.post("/api/v1/chat", json={"message": "ping"})
    assert response.status_code != 404
