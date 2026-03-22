import sys
sys.path.append('.')
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

try:
    from backend.main import app
except ImportError:
    from main import app

client = TestClient(app)

@patch('backend.main.get_db')
@patch('backend.main.use_credits')
@patch('backend.main.generate_quote_image')
def test_generate_image_sync(mock_gen, mock_credits, mock_db):
    """Test synchronous image generation."""
    # Mock credits check to pass
    mock_credits.return_value = True
    
    # Mock image generation to return dummy bytes
    from io import BytesIO
    mock_gen.return_value = BytesIO(b"dummy_image_data")
    
    # Force USE_CELERY=false for this test
    with patch('os.getenv', side_effect=lambda k, d=None: "false" if k == "USE_CELERY" else d):
        resp = client.post('/generate_image', json={'text': 'Test quote', 'mood': 'zen'})
        
    assert resp.status_code == 200
    assert "image_b64" in resp.json()

@patch('backend.main.get_db')
@patch('backend.main.use_credits')
@patch('backend.tasks.generate_image_task.delay')
def test_generate_image_async(mock_task, mock_credits, mock_db):
    """Test asynchronous image generation via Celery."""
    mock_credits.return_value = True
    mock_task.return_value.id = "test_task_id"
    
    # Force USE_CELERY=true
    with patch('os.getenv', side_effect=lambda k, d=None: "true" if k == "USE_CELERY" else d):
        resp = client.post('/generate_image', json={'text': 'Test quote', 'mood': 'zen'})
        
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "test_task_id"
    assert resp.json()["status"] == "processing"

@patch('backend.main.get_db')
@patch('backend.main.verify_payment_signature')
@patch('backend.main.upgrade_user_tier')
def test_verify_payment(mock_upgrade, mock_verify, mock_db):
    """Test payment verification flow."""
    mock_verify.return_value = True
    
    payload = {
        "razorpay_order_id": "order_123",
        "razorpay_payment_id": "pay_123",
        "razorpay_signature": "sig_123",
        "plan": "pro"
    }
    
    # Mock current_user dependency
    from backend.models import Users
    mock_user = Users(id=1, username="testuser", tier="free")
    
    with patch('backend.main.get_current_user', return_value=mock_user):
        resp = client.post('/verify_payment', json=payload)
        
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    mock_upgrade.assert_called_once()
