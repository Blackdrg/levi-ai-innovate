from fastapi.testclient import TestClient # type: ignore
from backend.main import app
import pytest # type: ignore

client = TestClient(app)

def test_heart_root():
    """Verify that the unified heart root is active."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["heart"] == "LEVI v6"

def test_heart_health():
    """Verify the production-grade health check logic in the main heart."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data

def test_heart_auth_mount(app_client):
    """Verify that auth router is correctly mounted on the unified heart."""
    response = app_client.post("/api/v1/user/auth/login", json={"email": "test@example.com", "password": "password"})
    # Adjusting for prefix stripping and modular routing
    assert response.status_code != 404

def test_heart_chat_mount():
    """Ensure Chat router is correctly mounted."""
    response = client.post("/api/v1/chat", json={"message": "ping"})
    assert response.status_code != 404
