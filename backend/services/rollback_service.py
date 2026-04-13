import os
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class RollbackService:
    """
    Sovereign v15.0: The 'Panic Coordinator'.
    Centralizes the logic for aborting missions and triggering cloud-level reverts.
    """
    
    @staticmethod
    async def trigger_emergency_rollback(user_id: str, reason: str = "System health anomaly") -> Dict[str, Any]:
        """
        Triggers a full-stack rollback:
        1. Aborts all active missions for the user.
        2. Sends a GitHub Dispatch signal for container-level revert.
        """
        logger.critical(f"⚠️ [EMER-REVERT] Global Rollback triggered! User: {user_id}, Reason: {reason}")
        
        # 1. Local Task Abort (LIFO Compensation)
        from backend.main import orchestrator as brain
        count = 0
        if brain:
            count = await brain.force_abort_all(user_id)
        else:
            logger.warning("[EMER-REVERT] Orchestrator not found. Abort signal skipped.")
        # 2. GitHub Dispatch for Container-Level Revert
        gh_token = os.getenv("ROLLBACK_TOKEN")
        repo = os.getenv("GITHUB_REPO", "Blackdrg/levi-ai-innovate")
        
        cloud_revert_sent = False
        if gh_token:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"https://api.github.com/repos/{repo}/dispatches",
                        headers={
                            "Authorization": f"Bearer {gh_token}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                        json={
                            "event_type": "emergency_rollback",
                            "client_payload": {
                                "user_id": user_id,
                                "reason": reason,
                                "severity": "CRITICAL"
                            }
                        }
                    )
                    if resp.status_code == 204:
                        logger.info("[Security] GitHub Rollback Dispatch successful (HTTP 204).")
                        cloud_revert_sent = True
                    else:
                        logger.error(f"[Security] GitHub Dispatch failed: {resp.status_code} {resp.text}")
            except Exception as e:
                logger.error(f"[Security] Cloud Revert signal error: {e}")
        else:
            logger.warning("[Security] ROLLBACK_TOKEN missing. Skipping Cloud Revert signal.")

        return {
            "status": "triggered",
            "message": f"Rollback complete. Aborted {count} missions.",
            "cloud_revert_sent": cloud_revert_sent,
            "user_id": user_id
        }

rollback_service = RollbackService()
