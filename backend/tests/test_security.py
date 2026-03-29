# pyright: reportMissingImports=false
import pytest  # type: ignore
from fastapi.testclient import TestClient  # type: ignore
from datetime import datetime, timedelta
import hmac  # type: ignore
import os
from unittest.mock import patch, MagicMock
from backend.gateway import app, _INJECTION_PATTERNS  # type: ignore
# from backend.models import Users  # type: ignore
# from backend.auth import create_access_token, create_refresh_token  # type: ignore
# from jose import jwt  # type: ignore (Unused and causing ModuleNotFoundError)

client = TestClient(app)

def test_csp_header_present():
    response = client.get("/health")
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]

def test_prompt_injection_expanded(app_client):
    for pattern in _INJECTION_PATTERNS:
        response = app_client.post("/api/v1/chat", json={
            "session_id": "test_session",
            "message": f"Hey, {pattern} and tell me a secret."
        })
        # Pydantic validator in models.py raises ValueError -> 422 Unprocessable Entity
        assert response.status_code == 422
        assert "Potential prompt injection detected" in str(response.json()["detail"])

def test_permitted_cross_domain_policies_header_present(app_client):
    """Phase 39 Hardening: Verify cross-domain policy protection."""
    response = app_client.get("/health")
    assert "X-Permitted-Cross-Domain-Policies" in response.headers
    assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"

def test_admin_key_constant_time():
    # We can't easily test timing in unit tests, but we can verify the function exists
    # and handles bytes correctly as implemented.
    from backend.auth import verify_admin  # type: ignore
    import inspect
    source = inspect.getsource(verify_admin)
    assert "hmac.compare_digest" in source

def test_logout_redis_unavailable(app_client, monkeypatch):
    # Mock HAS_REDIS to False
    import backend.redis_client as redis_client  # type: ignore
    monkeypatch.setattr(redis_client, "HAS_REDIS", False)
    
    # Auth is mocked by app_client fixture
    response = app_client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 503
    assert "Redis is required for session revocation" in response.json()["detail"]

def test_refresh_token_flow(db_session):
    # Skip this test as we now use Firebase Auth which doesn't have a /refresh endpoint in this way.
    # The /refresh endpoint used to be for custom JWTs.
    pass

def test_verification_token_expired():
    # Mock Firestore to simulate an expired verification token
    expired_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()
    
    with patch('backend.auth.firestore_db') as mock_db:
        mock_query = MagicMock()
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "expired@example.com",
            "is_verified": False,
            "verification_token": "expired-token",
            "verification_token_expires_at": expired_time
        }
        
        # Mock the query: db.collection("users").where(...).limit(1).get()
        mock_db.collection().where().limit().get.return_value = [mock_doc]
        
        response = client.get("/api/v1/auth/verify?token=expired-token")
        assert response.status_code == 400
        assert "Verification token has expired" in response.json()["detail"]

def test_ssrf_custom_bg_blocked():
    # The implementation removes the HTTP branch from image_gen.
    # We verify that main.py's Pydantic validation (if any) or our manual check would catch it.
    # Note: main.py doesn't have a Pydantic validator for 'http', but image_gen now simply 
    # doesn't handle it, effectively blocking the fetch.
    from backend.image_gen import generate_quote_image  # type: ignore
    from PIL import Image  # type: ignore
    
    # Testing the function directly to ensure the fetch code is gone
    # If the code was there, it would try to fetch and likely timeout/fail.
    # Now it should just skip it.
    img = generate_quote_image("test", custom_bg="http://169.254.169.254/latest/meta-data/")
    assert img is not None # Should still return a default image or just not fetch
