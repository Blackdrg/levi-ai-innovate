"""
Sovereign Audit Logger v14.0.0.
Handles immutable append-only recording of system-critical events.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy import select, desc
from backend.db.models import AuditLog
from backend.db.postgres_db import get_write_session, get_read_session

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Centralized service for cryptographic audit logging.
    Ensures every row is linked to the previous one via SHA-256 hash.
    """

    @classmethod
    async def log_event(
        cls,
        event_type: str,
        action: str,
        user_id: str = "system",
        resource_id: Optional[str] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Records an event in the audit_log table with integrity chaining.
        """
        async with get_write_session() as session:
            # 1. Fetch previous checksum for chaining
            # In a partitioned table, we might need to be careful with ordering
            stmt = select(AuditLog.checksum).order_by(desc(AuditLog.created_at)).limit(1)
            result = await session.execute(stmt)
            prev_checksum = result.scalar() or "GENESIS_BLOCK_0"

            # 2. Prepare row data
            row_data = {
                "event_type": event_type,
                "user_id": user_id,
                "resource_id": resource_id,
                "action": action,
                "status": status,
                "metadata_json": metadata or {}
            }

            # 3. Calculate checksum
            checksum = AuditLog.calculate_checksum(prev_checksum, row_data)

            # 4. Create record
            audit_entry = AuditLog(
                **row_data,
                checksum=checksum,
                created_at=datetime.now(timezone.utc)
            )
            
            session.add(audit_entry)
            # Commit is handled by get_write_session context manager
            logger.info(f"[Audit] Logged {event_type} event: {action} (User: {user_id})")

    @classmethod
    async def verify_chain_integrity(cls) -> bool:
        """
        Nightly Integrity Check: Re-calculates all checksums in the chain.
        Returns True if the chain is untampered.
        """
        async with get_read_session() as session:
            stmt = select(AuditLog).order_by(AuditLog.created_at)
            result = await session.execute(stmt)
            records = result.scalars().all()

            prev_checksum = "GENESIS_BLOCK_0"
            for record in records:
                row_data = {
                    "event_type": record.event_type,
                    "user_id": record.user_id,
                    "resource_id": record.resource_id,
                    "action": record.action,
                    "status": record.status,
                    "metadata_json": record.metadata_json
                }
                expected_checksum = AuditLog.calculate_checksum(prev_checksum, row_data)
                if record.checksum != expected_checksum:
                    logger.error(f"[Audit] Integrity Violation at Record ID {record.id}! Chain broken.")
                    return False
                prev_checksum = record.checksum
            
            return True
