"""
Sovereign Audit Chain Validator v15.0.
Verifies the cryptographic integrity of the entire AuditLog table.
"""

import sys
import asyncio
import logging
from backend.utils.audit import AuditLogger
from backend.db.postgres_db import verify_resonance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AuditValidator")

async def validate_audit_chain():
    logger.info("🛡️ Initiating Sovereign Audit Chain Validation...")
    
    # 1. Verify Database Resonance
    if not await verify_resonance():
        logger.error("❌ SQL Resonance link severed. Cannot validate.")
        sys.exit(1)
        
    # 2. Verify Cognitive Kernel Status (v15.1)
    from backend.kernel.kernel_wrapper import kernel
    if not kernel.rust_kernel:
        logger.warning("⚠️ COGNITIVE KERNEL OFFLINE: System in fallback [DEGRADED] mode.")
    else:
        logger.info("⚡ COGNITIVE KERNEL ONLINE: High-performance paths available.")
    
    # 2. Run Integrity Check
    try:
        is_valid = await AuditLogger.verify_chain_integrity()
        
        if is_valid:
            logger.info("✅ SUCCESS: Audit Ledger integrity verified. HMAC chain is intact.")
        else:
            logger.critical("🚨 CRITICAL FAILURE: Audit Ledger COMPROMISED! Integrity chain broken.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Validation process crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(validate_audit_chain())
