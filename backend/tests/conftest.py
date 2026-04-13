import pytest
import os
import asyncio
from typing import Generator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 🛡️ Sovereign v15.0: Test Environment Guarding
# Force ENVIRONMENT to 'testing' to trigger safety gates
os.environ["ENVIRONMENT"] = "testing"
os.environ["POSTGRES_DB"] = "levi_test_db"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Sets up a temporary in-memory or isolated test database."""
    test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/levi_test_db")
    engine = create_async_engine(test_db_url, echo=False)
    
    # In a full CI pipeline, we'd run migrations here
    # from backend.db.models import Base
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    """Provides a transactional session for each test."""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback() # Always rollback to keep tests isolated
