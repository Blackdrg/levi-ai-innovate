# Refactored conftest.py for Firestore-native architecture
import pytest
import sys
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Ensure the backend is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables BEFORE any backend imports
os.environ["ENVIRONMENT"] = "development"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_MESSAGING_SENDER_ID"] = "12345678"
os.environ["SECRET_KEY"] = "9342502788e0ef3e86f80907a78370de86121f0084323e0ef3e86f8c407a7837"
os.environ["RAZORPAY_KEY_ID"] = "test"
os.environ["RAZORPAY_KEY_SECRET"] = "test"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test"
os.environ["ADMIN_KEY"] = "test"

# Lazy imports to handle potential circular issues or startup failures
@pytest.fixture(scope="session")
def app():
    from backend.main import app as fastapi_app
    return fastapi_app

@pytest.fixture
def test_user():
    """Return a mock user dict matching Firestore schema."""
    return {
        "uid": "user_123",
        "username": "testuser",
        "email": "test@example.com",
        "tier": "free",
        "credits": 10
    }

@pytest.fixture(autouse=True)
def override_dependencies(app, test_user):
    """Override FastAPI dependencies for testing."""
    from backend.main import get_current_user, get_current_user_optional
    
    # Mock current user
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_current_user_optional] = lambda: test_user
    
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    """Return valid mock headers for the test user."""
    return {"Authorization": "Bearer fake_firebase_token"}

@pytest.fixture
def app_client(app):
    """Test client fixture."""
    return TestClient(app)

@pytest.fixture
def db_session():
    """Mock DB session for legacy code compatibility."""
    return MagicMock()
