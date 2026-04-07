"""
Sovereign Postgres SQL Fabric v14.0.0.
High-fidelity asynchronous session management for the Sovereign OS.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)
Base = declarative_base()

# --- v14.0.0 Engine Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif not DATABASE_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# High-concurrency engine (v14.0 tuning)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
) if DATABASE_URL else None

SessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
) if engine else None

class PostgresDB:
    """
    Sovereign Postgres Compatibility Bridge (v14.0.0).
    Maps legacy v13 PostgresDB calls to the new v14 SQL Fabric.
    """
    @staticmethod
    def _session_factory():
        if SessionLocal is None:
            raise ConnectionError("[Postgres-v13] Session factory not initialized.")
        return SessionLocal()
    
    @classmethod
    async def get_session(cls) -> AsyncSession:
        return cls._session_factory()

# --- Session Generators ---

@asynccontextmanager
async def get_read_session() -> AsyncGenerator[AsyncSession, None]:
    """ Asynchronous context manager for read-only SQL missions. """
    if SessionLocal is None:
        raise ConnectionError("[Postgres-v13] Engine not initialized. DATABASE_URL missing.")
    
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@asynccontextmanager
async def get_write_session() -> AsyncGenerator[AsyncSession, None]:
    """ Asynchronous context manager for mission-critical write resonance. """
    if SessionLocal is None:
        raise ConnectionError("[Postgres-v13] Engine not initialized. DATABASE_URL missing.")
    
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"[Postgres-v13] Transaction drift detected: {e}")
            raise
        finally:
            await session.close()

async def verify_resonance() -> bool:
    """
    Verifies that the Postgres connectivity is established and responsive.
    Crucial for the Graduation Startup Audit.
    """
    if not engine:
        return False
    try:
        async with get_read_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"[Postgres-v13] Resonance check failed: {e}")
        return False

async def close_resonance():
    """ Safely sever the SQL link. """
    if engine:
        await engine.dispose()
        logger.info("Sovereign SQL Resonance Link severed.")
