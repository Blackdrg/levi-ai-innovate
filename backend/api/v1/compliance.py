from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import logging

from backend.auth.logic import verify_admin
from backend.utils.audit import AuditLogger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compliance", tags=["Compliance & Audit"])

@router.get("/verify")
async def verify_audit_ledger(is_admin: bool = Depends(verify_admin)):
    """
    Sovereign v15.0 GA: Cryptographic Chain Verification.
    Performs a deep integrity check of the Audit Ledger.
    """
    try:
        is_untampered = await AuditLogger.verify_chain_integrity()
        
        if is_untampered:
            return {
                "status": "verified",
                "integrity": "untampered",
                "message": "Audit ledger chain is cryptographically sound."
            }
        else:
            return {
                "status": "compromised",
                "integrity": "violation",
                "message": "CRITICAL: Audit ledger integrity violation detected!"
            }
    except Exception as e:
        logger.error(f"[Compliance] Verification failure: {e}")
        raise HTTPException(status_code=500, detail="Audit verification stream offline.")

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_verified_logs(
    limit: int = 50,
    is_admin: bool = Depends(verify_admin)
):
    """
    Retrieves the latest audit logs with real-time integrity verification.
    """
    try:
        logs = await AuditLogger.get_verified_logs(limit=limit)
        return logs
    except Exception as e:
        logger.error(f"[Compliance] Log retrieval failure: {e}")
        raise HTTPException(status_code=500, detail="Audit log stream offline.")
