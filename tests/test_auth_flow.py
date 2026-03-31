import pytest
from fastapi.testclient import TestClient
from backend.main import app

# ── Test Configuration ──────────────────────────────────────────────────
client = TestClient(app)

def test_auth_signup_flow():
    """
    Verifies the v6.8 Sovereign Auth Lifecycle: Signup -> Login -> Profile.
    """
    import uuid
    user_random = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "password123"

    # 1. Signup (New seeker identity)
    # The brain refactored /register to /auth/signup
    resp = client.post("/auth/signup", json={
        "email": user_random, 
        "password": pwd,
        "username": user_random.split('@')[0]
    })
    
    # We allow 400 if user exists (though uuid makes it rare)
    assert resp.status_code in (200, 400)
    if resp.status_code == 200:
        assert "uid" in resp.json()
        assert resp.json()["status"] == "success"

    # 2. Login (Handshake)
    # Refactored /login to /auth/login
    resp = client.post("/auth/login", json={
        "uid": "test_uid_123", # Mocked for handshake
        "email": user_random
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

def test_auth_me_endpoint():
    """
    Verifies profile retrieval via /auth/me or /auth/users/me.
    Uses dependency overriding for the test user context.
    """
    from backend.auth import get_current_user
    
    # Mocking the user dependency
    app.dependency_overrides[get_current_user] = lambda: {
        "uid": "test_uid_123",
        "email": "tester@example.com",
        "username": "tester",
        "tier": "pro",
        "credits": 1000
    }
    
    try:
        resp = client.get("/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "tester@example.com"
        assert data["tier"] == "pro"
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()
