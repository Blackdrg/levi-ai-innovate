# pyright: reportMissingImports=false
"""API Tests."""
import sys
import os
from io import BytesIO
import pytest
from unittest.mock import patch, MagicMock


# conftest.py in the same directory will automatically provide fixtures
# but we still need basic imports for mocking

from backend.gateway import app
from backend.auth import get_current_user  # type: ignore

# Globally mock get_current_user for all tests in this file - now handled by conftest.py's app_client fixture
@pytest.fixture(autouse=True)
def mock_firebase_auth():
    """Still patch firebase_auth just in case some logic uses it directly."""
    with patch('backend.auth.firebase_auth.verify_id_token') as mock_verify:
        mock_verify.return_value = {'uid': 'user_123', 'email': 'test@example.com'}
        yield mock_verify


def test_health(app_client):
    """Test health."""
    resp = app_client.get('/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'

@patch('backend.services.chat.router.generate_response')
def test_chat(mock_gen_resp, app_client, test_user, auth_headers):
    """Test chat."""
    mock_gen_resp.return_value = 'hi'
    resp = app_client.post('/api/v1/chat', json={'session_id': '1', 'message': 'hi'}, headers=auth_headers)
    assert resp.status_code == 200

@patch('backend.firestore_db.db')
def test_search_quotes(mock_db, app_client):
    """Test search."""
    resp = app_client.post('/api/v1/gallery/search_quotes', json={'text': 'test'})
    assert resp.status_code == 200

@patch('backend.firestore_db.db')
def test_analytics(mock_db, app_client):
    """Test analytics."""
    resp = app_client.get('/api/v1/analytics')
    assert resp.status_code == 200

@patch('backend.services.studio.router.use_credits')
@patch('backend.image_gen.generate_quote_image')
@patch('backend.firestore_db.db')
def test_generate_image_auth(mock_db, mock_gen, mock_credits, app_client, test_user, auth_headers):
    """Test generate_image with auth override."""
    # Mock generate_quote_image to return a dict with a BytesIO data object (simulating real engine)
    mock_gen.return_value = {
        "success": True, 
        "data": BytesIO(b"fake_image_bytes"), 
        "engine": "mock_engine"
    }
    
    resp = app_client.post('/api/v1/studio/generate_image', json={'text': 'Wisdom'}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    assert "task_id" in resp.json()

@patch('backend.payments.verify_razorpay_signature')
@patch('backend.firestore_db.db')
def test_verify_payment_patch(mock_db, mock_verify, app_client, test_user, auth_headers):
    """Test verify_payment with correct upgrade_user_tier patch path."""
    mock_verify.return_value = True
    with patch('backend.payments.upgrade_user_tier') as mock_upgrade:
        resp = app_client.post('/api/v1/payments/verify_payment', json={
            'razorpay_order_id': 'order_123',
            'razorpay_payment_id': 'pay_123',
            'razorpay_signature': 'sig_123',
            'plan': 'pro'
        }, headers=auth_headers)
    assert resp.status_code == 200
    mock_upgrade.assert_called_once()
