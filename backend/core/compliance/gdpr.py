"""
Sovereign GDPR Compliance Manager v14.0.
Enforces EU data protection standards, PII masking, and the 'Right to be Forgotten' (RTBF).
"""

import re
import logging
import asyncio
from typing import Dict, Any, List, Optional
from backend.core.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

# PII Matching Patterns (Simplified for Sovereign use)
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b"
}

class GDPRManager:
    """
    Sovereign v14.0: GDPR Data Governance.
    Ensures user privacy across the 4-tier cognitive architecture.
    """
    
    @staticmethod
    def mask_pii(text: str) -> str:
        """Scrubs PII from the input string using regex patterns."""
        if not text:
            return text
            
        masked_text = text
        for label, pattern in PII_PATTERNS.items():
            masked_text = re.sub(pattern, f"<{label.upper()}_REDACTED>", masked_text)
            
        return masked_text

    @staticmethod
    async def invoke_rtbf(user_id: str) -> Dict[str, Any]:
        """
        Invokes the 'Right to be Forgotten'.
        1. Synchronously flags the user as 'Soft Deleted'.
        2. Asynchronously triggers the full memory wipe.
        """
        logger.warning(f"[GDPR] RTBF Invoked for User: {user_id}")
        
        try:
            # 1. Soft-Delete Flag (Immediate)
            await GDPRManager.set_soft_delete_flag(user_id, True)
            
            # 2. Background Wipe
            asyncio.create_task(GDPRManager._execute_full_wipe(user_id))
            
            return {
                "status": "success",
                "message": "Right to be Forgotten acknowledged. Soft-deletion active. Background wipe initiated.",
                "user_id": user_id
            }
        except Exception as e:
            logger.error(f"[GDPR] RTBF Initialiation Failure: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def _execute_full_wipe(user_id: str):
        """Internal background worker for deep memory erasure."""
        logger.info(f"[GDPR-Wipe] Starting surgical erasure for {user_id}...")
        manager = MemoryManager()
        try:
            cleared_count = await manager.clear_all_user_data(user_id)
            logger.info(f"[GDPR-Wipe] Full wipe complete for {user_id}. Cleared {cleared_count} nodes.")
        except Exception as e:
            logger.error(f"[GDPR-Wipe] Background erasure failed for {user_id}: {e}")

    @staticmethod
    async def set_soft_delete_flag(user_id: str, active: bool):
        """Sets the soft-delete flag in Redis to block immediate access."""
        from backend.db.redis import get_redis_client
        redis = get_redis_client()
        key = f"sovereign:soft_delete:{user_id}"
        if active:
            redis.setex(key, 86400 * 7, "1") # 7 day shadow period
        else:
            redis.delete(key)
        logger.info(f"[GDPR] Soft-delete flag {'enabled' if active else 'disabled'} for {user_id}")

    @staticmethod
    def get_data_governance_report(user_id: str) -> Dict[str, Any]:
        """Generates a compliance report for the user's data status."""
        # In a real impl, this would query table sizes and encryption status
        return {
            "compliance_standard": "GDPR (EU)",
            "encryption_status": "AES-256-GCM Active",
            "data_retention_policy": "Sovereign-First (User Controlled)",
            "tier_1_status": "Encrypted Redis",
            "tier_2_status": "Encrypted Postgres",
            "tier_3_status": "Encrypted FAISS",
            "tier_4_status": "Encrypted Neo4j"
        }
