"""
Sovereign Health Audit v9.8.1.
Verifies production readiness and service integrity for the Sovereign OS.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# To allow importing from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("health_checker")

async def check_redis():
    """Verifies Redis Pulse."""
    try:
        from backend.db.redis import r, HAS_REDIS
        if not HAS_REDIS or not r:
            return False, "Redis connection failed or not configured."
        r.ping()
        return True, "Redis PULSE active."
    except Exception as e:
        return False, f"Redis error: {e}"

async def check_postgres():
    """Verifies Postgres Tier 4 Connection."""
    try:
        from backend.db.postgres import PostgresDB
        async with PostgresDB._session_factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        return True, "Postgres TIER 4 resilient."
    except Exception as e:
        return False, f"Postgres error: {e}"

async def check_celery():
    """Verifies Swarm Cluster discovery."""
    try:
        from backend.celery_app import celery_app
        i = celery_app.control.inspect()
        active = i.active()
        if not active:
            return False, "No active SWARM workers found."
        return True, f"Swarm Cluster linked: {len(active)} active nodes."
    except Exception as e:
        return False, f"Celery error: {e}"

async def check_vector_db():
    """Verifies Vector Index integrity."""
    try:
        from backend.utils.vector_db import get_vector_db
        vdb = get_vector_db()
        count = vdb.index.ntotal
        return True, f"Vector Index operational ({count} fragments)."
    except Exception as e:
        return False, f"Vector error: {e}"

async def run_audit():
    """Executes the full Sovereign Audit."""
    print("=" * 50)
    print(f"LEVI-AI SOVEREIGN AUDIT v9.8.1 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    checks = [
        ("REDIS", check_redis()),
        ("POSTGRES", check_postgres()),
        ("CELERY", check_celery()),
        ("VECTOR_DB", check_vector_db())
    ]
    
    all_passed = True
    for name, coro in checks:
        success, msg = await coro
        status = " [OK]" if success else "[FAIL]"
        print(f"{name:12} {status} - {msg}")
        if not success:
            all_passed = False
            
    print("=" * 50)
    if all_passed:
        print("RESULT: SOVEREIGN ALIGNED")
    else:
        print("RESULT: SYSTEM DRIFT DETECTED - AUDIT FAILED")
    print("=" * 50)
    
    return all_passed

if __name__ == "__main__":
    passed = asyncio.run(run_audit())
    sys.exit(0 if passed else 1)
