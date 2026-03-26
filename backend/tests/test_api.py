# pyright: reportMissingImports=false
"""API Tests."""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock


# conftest.py in the same directory will automatically provide fixtures
# but we still need basic imports for mocking

try:
    from backend.main import app, get_current_user  # type: ignore
except ImportError:
    from main import app, get_current_user  # type: ignore

# Globally mock get_current_user for all tests in this file
@pytest.fixture(autouse=True)
def mock_auth(test_user):
    with patch('backend.main.firebase_auth.verify_id_token') as mock_verify:
        mock_verify.return_value = {"uid": "test_uid", "email": "test@example.com"}
        with patch('backend.main.get_current_user') as mock_get_user:
            mock_get_user.return_value = test_user
            yield


def test_health(app_client):
    """Test health."""
    resp = app_client.get('/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'

@patch('backend.main.get_db')
@patch('backend.main.generate_with_active_model')
@patch('backend.main.generate_response')
def test_chat(mock_gen_resp, mock_gen_active, mock_db, app_client, test_user, auth_headers):
    """Test chat."""
    mock_db.return_value = [MagicMock()]
    mock_gen_active.return_value = 'hi'
    mock_gen_resp.return_value = 'hi'
    resp = app_client.post('/chat', json={'session_id': '1', 'message': 'hi'}, headers=auth_headers)
    assert resp.status_code == 200

@patch('backend.main.get_db')
def test_search_quotes(mock_db, app_client):
    """Test search."""
    resp = app_client.post('/search_quotes', json={'text': 'test'})
    assert resp.status_code == 200

@patch('backend.main.get_db')
def test_analytics(mock_db, app_client):
    """Test analytics."""
    resp = app_client.get('/analytics')
    assert resp.status_code == 200

@patch('backend.main.use_credits')
@patch('backend.main.generate_quote_image')
@patch('backend.main.get_db')
def test_generate_image_auth(mock_db, mock_gen, mock_credits, app_client, test_user, auth_headers):
    """Test generate_image with auth override."""
    mock_gen.return_value = MagicMock()
    mock_gen.return_value.getvalue.return_value = b"fake_image_data"
    with patch.dict(os.environ, {"USE_CELERY": "false"}):
        resp = app_client.post('/generate_image', json={'text': 'Test quote', 'mood': 'zen'}, headers=auth_headers)
    assert resp.status_code == 200
    assert "image_b64" in resp.json()

@patch('backend.payments.verify_razorpay_signature')
@patch('backend.main.get_db')
def test_verify_payment_patch(mock_db, mock_verify, app_client, test_user, auth_headers):
    """Test verify_payment with correct upgrade_user_tier patch path."""
    mock_verify.return_value = True
    with patch('backend.payments.upgrade_user_tier') as mock_upgrade:
        resp = app_client.post('/verify_payment', json={
            'razorpay_order_id': 'order_123',
            'razorpay_payment_id': 'pay_123',
            'razorpay_signature': 'sig_123',
            'plan': 'pro'
        }, headers=auth_headers)
    assert resp.status_code == 200
    mock_upgrade.assert_called_once()
