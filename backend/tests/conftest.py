# pyright: reportMissingImports=false
import pytest  # type: ignore
import sys
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient  # type: ignore

# Ensure the backend is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables BEFORE any backend imports
os.environ["RENDER"] = "true"
os.environ["SECRET_KEY"] = "9342502788e0ef3e86f80907a78370de86121f0084323e0ef3e86f8c407a7837"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["RAZORPAY_KEY_ID"] = "test"
os.environ["RAZORPAY_KEY_SECRET"] = "test"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test"
os.environ["ADMIN_KEY"] = "test"

try:
    from backend import models, db, main  # type: ignore
    from backend.main import app, create_access_token  # type: ignore
    from backend.models import Users, Base  # type: ignore
    from backend.db import engine, SessionLocal  # type: ignore
except ImportError:
    import models, db, main  # type: ignore
    from main import app, create_access_token  # type: ignore
    from models import Users, Base  # type: ignore
    from db import engine, SessionLocal  # type: ignore

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test tables. Ensure all models are loaded."""
    # Re-import models to ensure they are registered on Base.metadata
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Database session fixture that rolls back after each test."""
    connection = engine.connect()
    # start a transaction
    transaction = connection.begin()
    # bind a session to the connection
    session = SessionLocal(bind=connection)
    
    # Create a nested transaction (SAVEPOINT) to handle any commits inside tests/routes
    # session.begin_nested() is already covered if we rollback the connection-level transaction
    # safely at the end, provided no full commits are pushed.
    # However, to avoid 'SessionAlreadyActive' or issues on commit, we just use the session.
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def override_get_db(db_session):
    """Override FastAPI get_db dependency to use the transactional session."""
    from backend.db import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()

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
