import pytest # type: ignore
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_env():
    """Ensure tests run with consistent environment variables."""
    with patch.dict("os.environ", {
        "SECRET_KEY": "test_secret",
        "RAZORPAY_KEY_ID": "rzp_test_123",
        "RAZORPAY_KEY_SECRET": "rzp_test_secret",
        "ADMIN_KEY": "admin_test",
        "FIREBASE_PROJECT_ID": "test-project",
        "FIREBASE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "ALERT_WEBHOOK_URL": "http://mock-webhook"
    }):
        yield

@pytest.fixture
def mock_firestore():
    """Mock the Firestore DB instance."""
    with patch("backend.firestore_db.db") as mock_db:
        yield mock_db

@pytest.fixture
def mock_redis():
    """Mock the Redis client instance."""
    with patch("backend.redis_client.r") as mock_r:
        mock_r.ping.return_value = True
        yield mock_r

@pytest.fixture
def test_user():
    return {
        "uid": "user_123",
        "email": "test@example.com",
        "username": "testuser",
        "tier": "free",
        "credits": 10,
        "role": "user"
    }
