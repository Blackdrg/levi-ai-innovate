import logging
import hmac
import hashlib
import json
import csv
import io
from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.db.postgres_db import get_write_session, get_read_session
from backend.db.models import SystemAudit
from sqlalchemy import select, text

logger = logging.getLogger(__name__)

# Secret for HMAC-SHA256 (Should be in .env)
SOVEREIGN_AUDIT_SECRET = "LEVI_AI_SOVEREIGN_AUDIT_SECRET_2026"

def generate_audit_signature(user_id: str, action: str, detail: str) -> str:
    """ Generates a deterministic HMAC-SHA256 integrity pulse for audit records. """
    msg = f"{user_id}|{action}|{detail}|{datetime.now(timezone.utc).date()}"
    return hmac.new(
        SOVEREIGN_AUDIT_SECRET.encode(), 
        msg.encode(), 
        hashlib.sha256
    ).hexdigest()

async def log_audit_action(user_id: str, action: str, resource_id: str = None, detail: str = "", ip_address: str = None, user_agent: str = None):
    """
    Sovereign Compliance Layer: Permanent Audit Pulsing.
    Registers every mission-critical interaction in the monolith ledger.
    """
    try:
        signature = generate_audit_signature(user_id, action, detail)
        
        async with get_write_session() as session:
            audit = SystemAudit(
                user_id=user_id,
                action=action,
                resource_id=resource_id,
                detail=detail,
                ip_address=ip_address,
                user_agent=user_agent,
                signature=signature
            )
            session.add(audit)
        
        logger.debug(f"[Compliance] Audit pulse synchronized: {action} by {user_id}")
    except Exception as e:
        logger.error(f"[Compliance] Audit failure: {e}")

async def export_audit_logs_csv(user_id: str, days: int = 30) -> str:
    """
    Sovereign Export: GDPR/HIPAA Artifact Generation.
    Generates a signed CSV of all audit records for the user.
    """
    try:
        async with get_read_session() as session:
            query = select(SystemAudit).where(
                SystemAudit.user_id == user_id,
                SystemAudit.created_at >= text(f"NOW() - INTERVAL '{days} days'")
            ).order_by(SystemAudit.created_at.desc())
            
            res = await session.execute(query)
            logs = res.scalars().all()
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Timestamp", "Action", "Resource", "Detail", "IP", "Signature"])
            
            for log in logs:
                writer.writerow([
                    log.id, 
                    log.created_at.isoformat(), 
                    log.action, 
                    log.resource_id, 
                    log.detail, 
                    log.ip_address, 
                    log.signature
                ])
                
            return output.getvalue()
    except Exception as e:
        logger.error(f"[Compliance] Export failure: {e}")
        return "Failed to manifest audit artifact."
