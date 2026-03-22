import pytest
import sys
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Ensure the backend is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Skip heavy model loading in tests
os.environ["RENDER"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-123"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["RAZORPAY_KEY_ID"] = "test"
os.environ["RAZORPAY_KEY_SECRET"] = "test"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test"
os.environ["ADMIN_KEY"] = "test"

try:
    from main import app, get_current_user, create_access_token
    from models import Users, Base
    from db import engine, SessionLocal
except ImportError:
    # Fallback for different test execution contexts
    sys.path.append('.')
    from backend.main import app, get_current_user, create_access_token
    from backend.models import Users, Base
    from backend.db import engine, SessionLocal

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Database session fixture that cleans up after each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def test_user(db_session):
    """Create a real user in the test database."""
    # Check if user already exists
    user = db_session.query(Users).filter(Users.username == "testuser").first()
    if not user:
        user = Users(
            id=1,
            username="testuser",
            password_hash="fakehash",
            tier="free",
            credits=10,
            is_verified=1
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    """Return valid JWT headers for the test user."""
    access_token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def app_client(db_session, test_user):
    """Test client fixture that ensures test user exists."""
    return TestClient(app)
