import pytest
import sys
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Ensure the backend is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import app, get_current_user
    from models import Users
except ImportError:
    # Fallback for different test execution contexts
    sys.path.append('.')
    from backend.main import app, get_current_user
    from backend.models import Users

@pytest.fixture
def app_client():
    """Test client fixture."""
    return TestClient(app)

@pytest.fixture
def mock_user():
    """Mock user fixture."""
    user = MagicMock(spec=Users)
    user.id = 1
    user.username = "testuser"
    user.tier = "free"
    user.credits = 10
    return user
