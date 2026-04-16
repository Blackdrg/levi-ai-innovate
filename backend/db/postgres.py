import os
import logging
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

logger = logging.getLogger(__name__)

Base = declarative_base()

class PostgresDB:
    """
    Sovereign Postgres Engine v8.
    Provides asynchronous session management for mission-critical persistence.
    """
    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                logger.warning("DATABASE_URL not found. Postgres will be unavailable.")
                return None
            
            # Convert postgres:// to postgresql+asyncpg:// if needed
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif not db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            # 🛡️ Graduation #23: Optimized HA Pooling
            cls._engine = create_async_engine(
                db_url,
                echo=False,
                pool_size=20,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                connect_args={
                    "server_settings": {
                        "application_name": "levi-orchestrator",
                        "jit": "off",
                    },
                    "timeout": 10,
                },
            )
            cls._session_factory = async_sessionmaker(
                cls._engine, 
                class_=AsyncSession, 
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            logger.info("Sovereign Postgres HA link established.")
        return cls._engine

    @classmethod
    async def get_session(cls) -> AsyncSession:
        """Standard session getter."""
        if cls._session_factory is None:
            cls.get_engine()
        
        if cls._session_factory:
            return cls._session_factory()
        return None

    @classmethod
    async def get_session_with_retry(cls, retries: int = 3) -> AsyncSession:
        """Acquire a verified session with bounded retry/backoff."""
        last_exc = None
        for attempt in range(retries):
            session = await cls.get_session()
            if not session:
                raise ConnectionError("Postgres session factory unavailable.")

            try:
                await session.execute(text("SELECT 1"))
                return session
            except Exception as exc:
                last_exc = exc
                await session.close()
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        raise last_exc

    @classmethod
    @asynccontextmanager
    async def session_scope(cls):
        """Transactional session scope management (Graduation #18)."""
        session = await cls.get_session_with_retry()
        if not session:
            logger.critical("[Postgres] Failed to acquire session scope.")
            raise ConnectionError("Postgres session unavailable.")
            
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @classmethod
    async def close(cls):
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("Sovereign Postgres link severed.")
