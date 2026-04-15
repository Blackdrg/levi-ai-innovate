"""
Sovereign v16.1 Audit Ledger Verifier.
Performs a full cryptographic sweep of the Postgres AuditLog table.
"""

import sys
import os
import asyncio
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load environment variables from .env
load_dotenv()

from backend.db.postgres import PostgresDB
from backend.db.models import AuditLog
from backend.utils.audit import verify_audit_chain as audit_verify_util
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuditVerifier")

async def verify_ledger():
    logger.info("🛡️ [AuditVerifier] Commencing Full Cryptographic Ledger Audit (v16.1)...")
    
    try:
        # Initialize the database engine
        PostgresDB.get_engine()
        
        async with PostgresDB._session_factory() as session:
            # 1. Fetch all audit logs in chronological order
            stmt = select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
            res = await session.execute(stmt)
            logs = res.scalars().all()
            
            if not logs:
                logger.warning("⚠️ [AuditVerifier] Audit ledger is empty. No missions to verify.")
                return

            logger.info(f"📊 [AuditVerifier] Found {len(logs)} entries. Verifying chain...")
            
            # 2. Perform Verification
            # We use the utility from backend.utils.audit
            is_valid = audit_verify_util(logs)
            
            if not is_valid:
                logger.error("🚨 [AuditVerifier] LEDGER CORRUPTION DETECTED! Cryptographic chain is broken.")
                sys.exit(1)
            
            logger.info(f"✨ [AuditVerifier] Ledger Verification SUCCESS. {len(logs)} entries confirmed authentic.")
            
    except Exception as e:
        logger.error(f"💥 [AuditVerifier] Verification Anomaly: {e}")
        if "relation \"audit_log\" does not exist" in str(e):
             logger.warning("⚠️ [AuditVerifier] Audit table not found. Skipping for fresh deployment.")
             sys.exit(0)
        sys.exit(1)
    finally:
        await PostgresDB.close()

if __name__ == "__main__":
    if not os.getenv("AUDIT_CHAIN_SECRET"):
        logger.warning("⚠️ [AuditVerifier] AUDIT_CHAIN_SECRET not set. Using default fallback (INSECURE).")
    
    asyncio.run(verify_ledger())
