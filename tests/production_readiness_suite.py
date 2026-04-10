import pytest
import os
import httpx
from backend.config.system import SECRET_KEY, ENVIRONMENT
from backend.utils.encryption import SovereignVault

def test_production_gate_fail_hard():
    """Verify that insecure secrets trigger SystemExit in production mode."""
    # We simulate production with a short secret
    os.environ["ENVIRONMENT"] = "production"
    os.environ["SECRET_KEY"] = "too-short"
    
    # Importing the function should trigger SystemExit or verify_production_secrets
    from backend.config.system import verify_production_secrets
    with pytest.raises(SystemExit) as excinfo:
        verify_production_secrets()
    assert "Must be at least 32 characters" in str(excinfo.value)
    
    # Restore env
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["SECRET_KEY"] = "sovereign_os_genesis_key_extended_for_test_32_chars"

def test_kms_envelope_encryption():
    """Verify that SovereignVault is using KMS envelope format (kms_v1:...)."""
    data = "Sensitive Sovereign Data"
    token = SovereignVault.encrypt(data)
    assert token.startswith("kms_v1:")
    
    decrypted = SovereignVault.decrypt(token)
    assert decrypted == data

def test_health_endpoints():
    """Verify production health endpoints are accessible (mocking actual server)."""
    # This would usually be an integration test against a live backend
    # Here we just verify the names/routes exist in the registry (conceptual)
    from backend.api.main import app
    routes = [route.path for route in app.routes]
    assert "/healthz" in routes
    assert "/api/v1/orchestrator/health/graph" in routes

def test_security_header_presence():
    """Verify Nginx-mocked headers or presence of security logic."""
    # In a real environment, we'd use 'curl -I' against the load balancer
    # Here we check the nginx.conf content for compliance
    with open("nginx.conf", "r") as f:
        content = f.read()
        assert "Strict-Transport-Security" in content
        assert "Content-Security-Policy" in content
        assert "X-Frame-Options" in content
