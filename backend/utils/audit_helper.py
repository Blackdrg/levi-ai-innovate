import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import select, desc
from backend.db.postgres import PostgresDB
from backend.db.models import AuditLog

logger = logging.getLogger(__name__)

class SovereignAuditHelper:
    """
    Sovereign v14.2 Forensic Audit Helper.
    Ensures non-repudiation via cryptographic checksum chaining.
    """
    
    @staticmethod
    async def record_event(
        event_type: str, 
        action: str, 
        user_id: Optional[str] = None, 
        resource_id: Optional[str] = None, 
        status: str = "success",
        metadata: Dict[str, Any] = {}
    ):
        """
        Records a high-fidelity audit event with integrity chaining.
        """
        try:
            async with PostgresDB._session_factory() as session:
                # 🛡️ 1. Fetch Previous Checksum for chaining
                prev_stmt = select(AuditLog.checksum).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(1)
                res = await session.execute(prev_stmt)
                prev_checksum = res.scalar_one_or_none() or "LEVI_GENESIS_v15_CHAIN_START"
                
                # 🛡️ 2. Build Row Data for hashing
                row_data = {
                    "event_type": event_type,
                    "user_id": user_id,
                    "resource_id": resource_id,
                    "action": action,
                    "status": status,
                    "metadata_json": metadata,
                    "created_at_fixed": datetime.now(timezone.utc).isoformat()
                }
                
                # 🛡️ 3. Calculate Integrity Hash
                checksum = AuditLog.calculate_checksum(prev_checksum, row_data)
                
                # 🛡️ 4. Persist
                log_entry = AuditLog(
                    event_type=event_type,
                    user_id=user_id,
                    resource_id=resource_id,
                    action=action,
                    status=status,
                    metadata_json=metadata,
                    checksum=checksum
                )
                session.add(log_entry)
                await session.commit()
                
                logger.info(f"[Forensics] Audit recorded: {action} on {resource_id} (Check: {checksum[:8]})")
                
    @staticmethod
    async def verify_audit_chain() -> bool:
        """
        Sovereign v15.0: Non-Repudiation Verification.
        Iterates through the entire audit ledger to verify cryptographic integrity.
        """
        try:
            async with PostgresDB._session_factory() as session:
                stmt = select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
                res = await session.execute(stmt)
                logs = res.scalars().all()
                
                if not logs:
                    return True
                
                prev_checksum = "LEVI_GENESIS_v15_CHAIN_START"
                for index, log in enumerate(logs):
                    row_data = {
                        "event_type": log.event_type,
                        "user_id": str(log.user_id) if log.user_id else None,
                        "resource_id": str(log.resource_id) if log.resource_id else None,
                        "action": log.action,
                        "status": log.status,
                        "metadata_json": log.metadata_json,
                        "created_at_fixed": log.created_at.isoformat()
                    }
                    
                    calculated = AuditLog.calculate_checksum(prev_checksum, row_data)
                    if calculated != log.checksum:
                        logger.critical(f"[Forensics] AUDIT CORRUPTION DETECTED at entry {log.id}! Expected {log.checksum[:8]}, got {calculated[:8]}")
                        return False
                    
                    prev_checksum = log.checksum
                
                logger.info(f"[Forensics] Audit ledger verified. {len(logs)} entries synchronized.")
                return True
                
        except Exception as e:
            logger.error(f"[Forensics] Audit verification failure: {e}")
            return False
