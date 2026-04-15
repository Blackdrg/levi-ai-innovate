"""
Sovereign Forensic Audit Utils v16.1 [HARDENED].
Handles cryptographic sign-off for mission events and cluster-wide ledger integrity.
"""

import os
import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def sign_event(prev_hash: str, event_data: dict) -> str:
    """
    Sovereign v16.1: Deterministic HMAC Chain Sign-off.
    FIXED: Uses canonical 'prev_hash || payload' message to prevent XOR collisions 
    or double-update non-determinism.
    """
    secret = os.getenv("AUDIT_CHAIN_SECRET", "levi_ai_genesis_key_v16_hardened_32_bytes")
    if len(secret) < 32:
        logger.warning("[Audit] Weak AUDIT_CHAIN_SECRET ( < 32 bytes). Using fallback entropy.")
        secret = secret.ljust(32, "!")
    
    # 1. Canonical Serialization
    payload = json.dumps(event_data, sort_keys=True).encode()
    
    # 2. Chained Message Construction (hash_n = HMAC(key, prev_hash + data))
    # Using '||' as a separator to ensure unambiguous boundaries
    msg = prev_hash.encode() + b"||" + payload
    
    # 3. HMAC-SHA256 Generation
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()

class AuditLogger:
    """
    Sovereign v15.0 GA: Forensic Audit Logger.
    """
    
    @staticmethod
    async def log_mission_event(mission_id: str, action: str, data: Dict[str, Any]):
        """Logs a mission-critical event to the PostgreSQL forensic ledger."""
        from backend.db.postgres import PostgresDB
        from backend.db.models import AuditLog
        from sqlalchemy import select
        
        try:
            async with PostgresDB._session_factory() as session:
                # 1. Fetch the last checksum for chaining
                # This ensures the chain is continuous across the cluster
                stmt = select(AuditLog.checksum).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(1)
                res = await session.execute(stmt)
                prev_checksum = res.scalar_one_or_none() or "GENESIS"
                
                # 2. Construct stable row data
                # We OMIT the dynamic 'now()' to ensure verification is deterministic
                row_data = {
                    "event_type": "MISSION",
                    "user_id": data.get("user_id", "system"),
                    "resource_id": mission_id,
                    "action": action,
                    "status": "success",
                    "metadata": data
                }
                
                # 3. Calculate consistent checksum using the model's logic
                checksum = AuditLog.calculate_checksum(prev_checksum, row_data)
                
                new_log = AuditLog(
                    event_type="MISSION",
                    user_id=data.get("user_id", "system"),
                    resource_id=mission_id,
                    action=action,
                    status="success",
                    metadata_json=data,
                    checksum=checksum
                )
                session.add(new_log)
                await session.commit()
                
                logger.info(f"🛡️ [Audit] Event signed: {action} (Mission: {mission_id}). Hash: {checksum[:8]}")
        except Exception as e:
            logger.error(f"[Audit] Failed to log forensic event: {e}")

class SystemAudit:
    """
    Sovereign v14.0.0-Autonomous-SOVEREIGN: Cryptographic chaining.
    """
    
    @staticmethod
    def calculate_signature(prev_sig: str, data: str) -> str:
        """
        FIXED: Standardized on sign_event pattern for consistency.
        """
        return sign_event(prev_sig, {"raw_data": data})

def verify_audit_chain(logs: list) -> bool:
    """Verifies the integrity of an audit log chain."""
    from backend.db.models import AuditLog
    
    prev_hash = "GENESIS"
    for log in logs:
        # Reconstruct row data exactly as it was during signing in AuditLogger
        row_data = {
            "event_type": log.event_type,
            "user_id": log.user_id,
            "resource_id": log.resource_id,
            "action": log.action,
            "status": log.status,
            "metadata": log.metadata_json
        }
        
        expected = AuditLog.calculate_checksum(prev_hash, row_data)
        if expected != log.checksum:
            logger.error(f"🚨 [Audit-Verify] Integrity violation at log {log.id} (Mission: {log.resource_id})")
            return False
            
        prev_hash = log.checksum
    return True
