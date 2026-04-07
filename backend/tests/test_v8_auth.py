"""
LEVI-AI Sovereign OS v8 - Auth Tier Tests.
Validates the Sovereign Shield security logic and model schemas.
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from backend.auth.models import UserProfile, AuthToken
from backend.auth.logic import SovereignAuth

def test_user_profile_schema():
    """Verify Pydantic validation for the v8 UserProfile."""
    user = UserProfile(
        uid="sov_123",
        username="neo",
        tier="pro",
        credits=500,
        created_at=datetime.now(timezone.utc),
        last_active=datetime.now(timezone.utc)
    )
    assert user.uid == "sov_123"
    assert user.tier == "pro"

def test_token_logic():
    """Verify basic token model representation."""
    token = AuthToken(access_token="quantum_pulse_xxxx")
    assert token.token_type == "bearer"
    assert "quantum_pulse" in token.access_token

@pytest.mark.asyncio
async def test_token_verification_failure():
    """Verify authentication guard handling for invalid pulses."""
    with patch('backend.auth.logic.auth') as mock_fb_auth:
        mock_fb_auth.verify_id_token.side_effect = Exception("Pulse invalid")
        
        # Should return None or raise consistent exception depending on strategy
        # Here we test the interface stability
        result = SovereignAuth.verify_token("invalid_token")
        assert result is None
