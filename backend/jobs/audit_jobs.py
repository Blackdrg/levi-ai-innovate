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
        
async def shadow_audit_graduated_rules():
    """
    Nightly Proactive Audit (v15.0 GA).
    Selects successful graduated rules and audits them against fresh LLM reasoning.
    Ensures that "fast-path" logic remains consistent with the latest cognitive standards.
    """
    logger.info("[AuditJobs] Initiating proactive Shadow Audit sweep...")
    from backend.db.models import GraduatedRule
    from backend.db.postgres_db import get_read_session
    from backend.core.orchestrator import _orchestrator
    from sqlalchemy import select
    
    async with get_read_session() as session:
        # Audit top 5 most recently used rules
        stmt = select(GraduatedRule).order_by(GraduatedRule.last_used_at.desc()).limit(5)
        rules = (await session.execute(stmt)).scalars().all()
        
        for rule in rules:
            logger.info(f"[AuditJobs] Proactively auditing Rule ID: {rule.id}")
            # Mocking a characteristic input if none stored, or use actual historical input
            # In a full impl, we'd pull from mission_metrics.
            # Here we follow the logic in orchestrator._perform_shadow_audit
            await _orchestrator._perform_shadow_audit(
                request_id=f"audit_{rule.id}",
                user_input=rule.task_pattern, # Pattern as input for verification
                rule_id=rule.id
            )

async def run_daily_compliance_sweep():
    """Entry point for Celery scheduler."""
    await nightly_audit_integrity_check()
    await enforce_audit_retention()
    await shadow_audit_graduated_rules()
