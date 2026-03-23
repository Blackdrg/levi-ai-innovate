# pyright: reportMissingImports=false
import sys
sys.path.append('.')
import pytest  # type: ignore
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient  # type: ignore
from io import BytesIO

try:
    from backend.main import app, get_current_user  # type: ignore
    from backend.models import Users  # type: ignore
except ImportError:
    from main import app, get_current_user  # type: ignore
    from models import Users  # type: ignore


# ── Shared mock user ──────────────────────────────────────────────────────────
def make_mock_user(tier="free", credits=10):
    user = MagicMock(spec=Users)
    user.id = 1
    user.username = "testuser"
    user.tier = tier
    user.credits = credits
    return user


# Override the auth dependency for the whole test module
@pytest.fixture(autouse=False)
def mock_auth(request):
    """Override get_current_user for tests that need it."""
    user = make_mock_user()
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ── Image generation (sync) ───────────────────────────────────────────────────
@patch('backend.payments.use_credits')
@patch('backend.image_gen.generate_quote_image')
def test_generate_image_sync(mock_gen, mock_credits, client, mock_auth):
    """Test synchronous image generation (USE_CELERY=false)."""
    mock_credits.return_value = 9
    mock_gen.return_value = BytesIO(b'\x89PNG\r\n' + b'\x00' * 100)

    with patch('os.getenv', side_effect=lambda k, d=None: (
        "false" if k == "USE_CELERY" else
        None if k == "AWS_S3_BUCKET" else
        d
    )):
        resp = client.post('/generate_image', json={
            'text': 'Test quote',
            'mood': 'zen',
            'author': 'Test'
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "image_b64" in data or "task_id" in data


# ── Image generation (async / Celery) ─────────────────────────────────────────
@patch('backend.payments.use_credits')
@patch('backend.tasks.generate_image_task')
def test_generate_image_async(mock_task, mock_credits, client, mock_auth):
    """Test async image generation via Celery."""
    mock_credits.return_value = 9
    mock_task.delay.return_value.id = "test_task_id_123"

    with patch('os.getenv', side_effect=lambda k, d=None: (
        "true" if k == "USE_CELERY" else d
    )):
        resp = client.post('/generate_image', json={
            'text': 'Test quote',
            'mood': 'zen',
            'author': 'Test'
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    assert "task_id" in data


# ── Payment verification ───────────────────────────────────────────────────────
# upgrade_user_tier is imported INSIDE the route body via
# "from backend.payments import upgrade_user_tier" — patch it there, not on main
@patch('backend.payments.upgrade_user_tier')
@patch('backend.payments.verify_payment_signature')
def test_verify_payment(mock_verify, mock_upgrade, client, mock_auth):
    """Test payment verification flow."""
    mock_verify.return_value = True

    payload = {
        "razorpay_order_id": "order_123",
        "razorpay_payment_id": "pay_123",
        "razorpay_signature": "sig_123",
        "plan": "pro"
    }

    resp = client.post('/verify_payment', json=payload)

    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    mock_upgrade.assert_called_once()
