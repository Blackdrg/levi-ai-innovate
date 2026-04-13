# backend/db/connection.py
import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# v15.0 Hardened Connection Layer
DATABASE_URL = os.getenv("DATABASE_URL")

# Production-grade pooling configuration
# 🛡️ Graduation #23: Pool Monitoring and Resiliency
engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "40")),
    pool_timeout=30.0,
    pool_recycle=1800.0,
    pool_pre_ping=True,
    echo=False
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to provide database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

class PostgresSessionManager:
    """Manages transactional scopes for non-FastAPI contexts."""
    @staticmethod
    async def get_scoped_session() -> AsyncSession:
        return async_session_factory()

logger.info("✅ Database connection layer initialized with QueuePool.")
