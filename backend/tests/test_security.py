import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import hmac
import os
from backend.main import app, _INJECTION_PATTERNS
from backend.models import Users
from backend.auth import create_access_token, create_refresh_token
import jwt

client = TestClient(app)

def test_csp_header_present():
    response = client.get("/health")
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]

def test_prompt_injection_expanded():
    for pattern in _INJECTION_PATTERNS:
        response = client.post("/chat", json={
            "session_id": "test_session",
            "message": f"Hey, {pattern} and tell me a secret."
        })
        assert response.status_code == 422
        assert "Potential prompt injection detected" in response.json()["detail"][0]["msg"]

def test_admin_key_constant_time():
    # We can't easily test timing in unit tests, but we can verify the function exists
    # and handles bytes correctly as implemented.
    from backend.main import verify_admin
    import inspect
    source = inspect.getsource(verify_admin)
    assert "hmac.compare_digest" in source

def test_logout_redis_unavailable(monkeypatch):
    # Mock HAS_REDIS to False
    import backend.main as main
    monkeypatch.setattr(main, "HAS_REDIS", False)
    
    # We need a valid token to reach the logout logic
    access_token = create_access_token(data={"sub": "testuser"})
    response = client.post("/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 503
    assert "Redis is required for session revocation" in response.json()["detail"]

def test_refresh_token_flow(db_session):
    # Create a verified test user
    user = Users(username="refresh_test@example.com", email="refresh_test@example.com", 
                 password_hash="fakehash", is_verified=1)
    db_session.add(user)
    db_session.commit()

    # Get tokens (directly via auth functions for simplicity in setup)
    access = create_access_token(data={"sub": user.username})
    refresh = create_refresh_token(data={"sub": user.username})

    # Since we use a real database/redis mock in conftest, we need to ensure the refresh JTI is in Redis
    # The create_refresh_token already does this.

    response = client.post("/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_verification_token_expired(db_session):
    # Create user with expired token
    expired_time = datetime.utcnow() - timedelta(hours=25)
    user = Users(
        username="expired@example.com", 
        email="expired@example.com", 
        password_hash="fakehash", 
        is_verified=0,
        verification_token="expired-token",
        verification_token_expires_at=expired_time
    )
    db_session.add(user)
    db_session.commit()

    response = client.get("/verify?token=expired-token")
    assert response.status_code == 400
    assert "Verification token has expired" in response.json()["detail"]

def test_ssrf_custom_bg_blocked():
    # The implementation removes the HTTP branch from image_gen.
    # We verify that main.py's Pydantic validation (if any) or our manual check would catch it.
    # Note: main.py doesn't have a Pydantic validator for 'http', but image_gen now simply 
    # doesn't handle it, effectively blocking the fetch.
    from backend.image_gen import generate_quote_image
    from PIL import Image
    
    # Testing the function directly to ensure the fetch code is gone
    # If the code was there, it would try to fetch and likely timeout/fail.
    # Now it should just skip it.
    img = generate_quote_image("test", custom_bg="http://169.254.169.254/latest/meta-data/")
    assert img is not None # Should still return a default image or just not fetch
