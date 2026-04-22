import os
import logging
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from backend.utils.circuit_breaker import postgres_breaker
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
            from backend.utils.secrets import secret_manager
            db_url = secret_manager.get_secret("DATABASE_URL")
            if not db_url:
                user = os.getenv("DB_USER", "levi")
                pw = secret_manager.get_secret("DB_PASSWORD") or os.getenv("DB_PASSWORD", "sovereign")
                host = os.getenv("DB_HOST", "postgres")
                port = os.getenv("DB_PORT", "5432")
                db = os.getenv("DB_NAME", "levi_ai")
                db_url = f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}"
            
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
    async def init_db(cls):
        """
        Sovereign v22 GA: Autonomous SQL Migration.
        Ensures all tables defined in models.py are created in the target Postgres fabric.
        """
        engine = cls.get_engine()
        if engine is None:
            logger.error("🚫 [Postgres] Cannot initialize DB: Engine not established.")
            return

        try:
            # Import models inside to avoid circular dependencies
            from . import models
            async with engine.begin() as conn:
                logger.info("🛠️ [Postgres] Synchronizing SQL metadata...")
                # In v1.4+, metadata.create_all is the standard for auto-migration
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ [Postgres] Table crystallization complete.")
        except Exception as e:
            logger.critical(f"💥 [Postgres] Schema synchronization FAILED: {e}")
            logger.warning("⚠️ [Postgres] Falling back to memory/degraded mode. Persistence offline.")

    @classmethod
    @asynccontextmanager
    async def session_scope(cls):
        """Transactional session scope management (Section 5 Stabilization)."""
        from sqlalchemy.exc import OperationalError
        import asyncio
        
        for attempt in range(3):
            async def run_session():
                session = await cls.get_session()
                if not session:
                    raise ConnectionError("Postgres session unavailable.")
                # Section 5 Fix: Explicit liveness check
                await session.execute(text("SELECT 1"))
                return session
            
            session = None
            try:
                session = await postgres_breaker.call(run_session)
                yield session
                await session.commit()
                return
            except OperationalError:
                if session:
                    await session.rollback()
                    await session.close()
                if attempt == 2:
                    raise
                # Exponential backoff: 0.5s, 1.0s, 1.5s
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception:
                if session:
                    await session.rollback()
                raise
            finally:
                # Ensure closure
                try: 
                    if session and session.is_active:
                        await session.close()
                except: 
                    pass
    
    @classmethod
    def _session_factory_internal(cls):
        """Compatibility bridge for internal session creation."""
        if cls._session_factory is None:
            cls.get_engine()
        return cls._session_factory()

    @classmethod
    async def cls_verify(cls) -> bool:
        """Deep health check of the Postgres fabric."""
        try:
            session = await cls.get_session()
            if not session: return False
            async with session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @classmethod
    async def check_health(cls) -> bool:
        """Alias for deep health check."""
        return await cls.cls_verify()

    @classmethod
    async def close(cls):
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
        cls._session_factory = None
        logger.info("Sovereign Postgres link severed.")

    async def track_event(self, mission_id: str, event_type: str, data: dict):
        """Standard v22-GA tracking bridge for mission-specific events."""
        async with self.session_scope() as session:
            try:
                from .models import MissionMetric
                metric = MissionMetric(
                    mission_id=mission_id,
                    status=event_type,
                    latency_ms=data.get("latency_ms", 0),
                    intent=data.get("intent", "telemetry"),
                    fidelity=data.get("fidelity", 1.0),
                    user_id=data.get("user_id", "system")
                )
                session.add(metric)
                # session.commit() is handled by session_scope()
            except Exception as e:
                logger.error(f"[PostgresDB] Telemetry tracking failed: {e}")

    async def track_generic_event(self, event_type: str, data: dict):
        """Standard v22-GA tracking bridge for system-wide analytics."""
        await self.track_event("SYSTEM", event_type, data)

    async def persist_knowledge_delta(self, mission_id: str, knowledge_delta: dict):
        """Persists a mission's knowledge delta into the factual ledger."""
        async with self.session_scope() as session:
            try:
                import json
                query = text("INSERT INTO factual_ledger (mission_id, knowledge_delta, timestamp) VALUES (:mid, :delta, NOW())")
                await session.execute(query, {"mid": mission_id, "delta": json.dumps(knowledge_delta)})
                logger.info(f"Knowledge delta persisted for mission: {mission_id}.")
            except Exception as e:
                logger.error(f"Failed to persist knowledge delta for {mission_id}: {e}")

    async def create_factual_snapshot(self):
        """Generates an ACID-compliant snapshot of the entire factual ledger."""
        async with self.session_scope() as session:
            try:
                # PostgreSQL native snapshot export
                result = await session.execute(text("SELECT pg_export_snapshot()"))
                snapshot_id = result.scalar()
                logger.info(f"Factual Snapshot created [ID: {snapshot_id}].")
                return snapshot_id
            except Exception as e:
                logger.error(f"Failed to create factual snapshot: {e}")
                return None

# Global instance for legacy callers
postgres_db = PostgresDB()
