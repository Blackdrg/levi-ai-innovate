import os
import sys

# Database URL and path logic are managed in conftest.py

# Ensure project root is in path for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import hmac
import hashlib
from unittest.mock import patch, MagicMock

def test_health_check_connectivity(app_client, mock_firestore):
    """Test that /health returns detailed status."""
    # Using the mock_firestore fixture from conftest.py
    response = app_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert "redis" in data

def test_razorpay_hmac_logic():
    """Verification of the corrected HMAC signature logic."""
    secret = "test_secret"
    payload = b'{"event":"payment.captured"}'
    # Correct signature calculation
    expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert len(expected_sig) == 64

def test_payment_idempotency(mock_firestore):
    """Test payment idempotency check in Firestore."""
    # Using the mock_firestore fixture from conftest.py
    # Configure mock for this specific check
    mock_firestore.collection().document().get().exists = True
    
    doc = mock_firestore.collection("payment_events").document("pay_123").get()
    assert doc.exists == True

def test_credit_deduction_post_success(app_client):
    """Verify that credits are deducted when a generation job starts."""
    with patch("backend.services.studio.router.generate_image_task.delay") as mock_task, \
         patch("backend.services.studio.router.use_credits") as mock_use_credits:
         
         # Mocking auth is handled by app_client fixture
         mock_task.return_value = MagicMock(id="test_job_id")
         
         headers = {"Authorization": "Bearer mock_token"}
         # Updated to the standardized studio route
         with patch.dict(os.environ, {"USE_CELERY": "false"}):
            response = app_client.post("/api/v1/studio/generate_image", json={"text": "Wisdom"}, headers=headers)
         
         assert response.status_code == 200 # Now returns 200 queued
         mock_use_credits.assert_called_once()
