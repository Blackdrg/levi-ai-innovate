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
    """Mock the Firestore DB instance with realistic defaults."""
    from datetime import datetime
    with patch("backend.firestore_db.db") as mock_db:
        # Configure a default document structure to avoid MagicMock vs datetime errors
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "count": 0,
            "last_reset": datetime.utcnow(),
            "credits": 10,
            "tier": "free",
            "last_used": datetime.utcnow()
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        yield mock_db

@pytest.fixture
def mock_redis():
    """Mock the Redis client instance."""
    with patch("backend.redis_client.r") as mock_r:
        mock_r.ping.return_value = True
        yield mock_r

@pytest.fixture
def auth_headers():
    """Mock bearer token for tests."""
    return {"Authorization": "Bearer mock_token"}

@pytest.fixture
def app_client(test_user):
    """FastAPI TestClient wrapping the Gateway app with auth overrides."""
    from fastapi.testclient import TestClient
    from backend.gateway import app
    from backend.auth import get_current_user, get_current_user_optional
    
    # Global overrides for all tests using app_client
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_user_optional] = lambda: test_user
    
    # Mock HAS_REDIS to True globally for the test client
    with patch("backend.gateway.HAS_REDIS", True):
        with patch("backend.services.analytics.router.HAS_REDIS", True):
            with patch("backend.auth.HAS_REDIS", True):
                client = TestClient(app)
                yield client
                # Clear overrides after test
                app.dependency_overrides = {}

@pytest.fixture
def db_session(mock_firestore):
    """Alias for mock_firestore to support legacy tests."""
    yield mock_firestore

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
