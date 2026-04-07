"""
Sovereign Audit Jobs v14.0.0.
Handles nightly integrity verification and 90-day retention policies for the Audit Log.
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete
from backend.utils.audit import AuditLogger
from backend.db.models import AuditLog
from backend.db.postgres_db import get_write_session

logger = logging.getLogger(__name__)

async def nightly_audit_integrity_check():
    """
    Verifies the cryptographic chain of the entire audit log.
    If any record has been modified or deleted, the check will fail.
    """
    logger.info("[AuditJobs] Starting nightly integrity verification...")
    is_valid = await AuditLogger.verify_chain_integrity()
    
    if is_valid:
        logger.info("[AuditJobs] Integrity check PASSED. Chain is secure.")
    else:
        logger.critical("[AuditJobs] Integrity check FAILED! Possible tampering detected.")
        # In a real system, this should trigger a high-priority alert (PagerDuty, etc.)

async def enforce_audit_retention():
    """
    90-Day Retention Policy: Prunes audit logs older than 90 days.
    Note: Since the table is partitioned, we should ideally drop the partition.
    For this implementation, we'll use a standard DELETE to ensure compliance.
    """
    logger.info("[AuditJobs] Enforcing 90-day retention policy...")
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    
    async with get_write_session() as session:
        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        result = await session.execute(stmt)
        pruned_count = result.rowcount
        
        logger.info(f"[AuditJobs] Pruned {pruned_count} expired audit records.")
        
async def run_daily_compliance_sweep():
    """Entry point for Celery scheduler."""
    await nightly_audit_integrity_check()
    await enforce_audit_retention()
