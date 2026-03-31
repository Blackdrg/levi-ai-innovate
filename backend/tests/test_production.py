# pyright: reportMissingImports=false
import sys
sys.path.append('.')
import pytest  # type: ignore
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient  # type: ignore

from backend.main import app # type: ignore

@patch('backend.firestore_db.db')
@patch('backend.services.studio.router.use_credits')
@patch('backend.image_gen.generate_quote_image')
def test_generate_image_sync(mock_gen, mock_credits, mock_db, app_client, auth_headers):
    """Test image generation with local background task (Sync behavior for test)."""
    mock_credits.return_value = True
    mock_gen.return_value = "data:image/png;base64,mock"
    
    # Mocking doc for rate limiting
    from datetime import datetime
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"count": 0, "last_reset": datetime.utcnow()}
    mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

    # Force USE_CELERY=false to use background_tasks fallback
    with patch('os.getenv', side_effect=lambda k, d=None: "false" if k == "USE_CELERY" else d):
        resp = app_client.post('/api/v1/studio/generate_image', json={'text': 'Test quote', 'mood': 'zen'}, headers=auth_headers)
        
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    assert "task_id" in resp.json()

@patch('backend.firestore_db.db')
@patch('backend.services.studio.router.use_credits')
@patch('backend.services.studio.router.generate_image_task.delay')
def test_generate_image_async(mock_task, mock_credits, mock_db, app_client, auth_headers):
    """Test asynchronous image generation via Celery."""
    mock_credits.return_value = True
    mock_task.return_value.id = "test_task_id"
    
    # Force USE_CELERY=true
    with patch('os.getenv', side_effect=lambda k, d=None: "true" if k == "USE_CELERY" else d):
        resp = app_client.post('/api/v1/studio/generate_image', json={'text': 'Test quote', 'mood': 'zen'}, headers=auth_headers)
        
    assert resp.status_code == 200 # Now returns 200 queued
    assert resp.json()["task_id"].startswith("job_")
    assert resp.json()["status"] == "queued"

@patch('backend.firestore_db.db')
@patch('backend.payments.verify_razorpay_signature')
@patch('backend.payments.upgrade_user_tier')
def test_verify_payment(mock_upgrade, mock_verify, mock_db, app_client, auth_headers):
    """Test payment verification flow."""
    mock_verify.return_value = True
    
    payload = {
        "razorpay_order_id": "order_123",
        "razorpay_payment_id": "pay_123",
        "razorpay_signature": "sig_123",
        "plan": "pro"
    }
    
    resp = app_client.post('/api/v1/payments/verify_payment', json=payload, headers=auth_headers)
        
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    mock_upgrade.assert_called_once()
