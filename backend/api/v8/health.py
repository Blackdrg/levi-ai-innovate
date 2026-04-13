# backend/api/v8/health.py
import logging
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Any, Dict
from backend.auth.logic import get_current_user
from backend.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Infrastructure Resilience"])

# Global Orchestrator Instance
orchestrator = Orchestrator()

@router.post("/rollback")
async def trigger_cluster_rollback(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    identity: Any = Depends(get_current_user)
):
    """
    Sovereign v15.0: Automated Cluster Revert.
    Triggers an emergency mission evacuation and initiates a GitHub Action 
    deployment rollback if the graduation score falls below threshold.
    """
    reason = payload.get("reason", "Unknown cognitive anomaly")
    threshold = float(os.getenv("ROLLBACK_THRESHOLD", "0.7"))
    
    # 1. Check current system integrity
    score = await orchestrator.get_graduation_score()
    
    if score < threshold or payload.get("force", False):
        logger.critical(f"🚨 [Resilience] System integrity ({score}) below threshold ({threshold}). TRIGGERING ROLLBACK.")
        
        # 2. Emergency Evacuation
        aborted_count = await orchestrator.force_abort_all("SYSTEM_AUTONOMOUS")
        
        # 3. GitHub Dispatch (Infrastructure Revert)
        background_tasks.add_task(_dispatch_github_rollback, reason, score)
        
        return {
            "status": "ROLLBACK_INITIATED",
            "score": score,
            "missions_aborted": aborted_count,
            "message": f"Emergency rollback triggered: {reason}"
        }
    
    return {
        "status": "STABLE",
        "score": score,
        "message": "System integrity within safe operating parameters."
    }

async def _dispatch_github_rollback(reason: str, score: float):
    """
    Sovereign v15.0: CI/CD Synchronization Layer.
    Dispatches a 'repository_dispatch' event to GitHub to trigger the 'Production Revert' workflow.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO") # e.g., "Blackdrg/levi-ai"
    
    if not github_token or not repo:
        logger.warning("[Resilience] GitHub credentials missing. Skipping infrastructure revert.")
        return

    async with httpx.AsyncClient() as client:
        try:
            url = f"https://api.github.com/repos/{repo}/dispatches"
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "event_type": "automated_cluster_revert",
                "client_payload": {
                    "reason": reason,
                    "graduation_score": score,
                    "timestamp": os.getenv("DEPLOY_TS", "v15-latest")
                }
            }
            resp = await client.post(url, headers=headers, json=data)
            if resp.status_code == 204:
                logger.info(f"✅ [Resilience] GitHub Dispatch Successful: {repo}")
            else:
                logger.error(f"❌ [Resilience] GitHub Dispatch Failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"[Resilience] Dispatch Exception: {e}")

@router.get("/readiness")
async def cluster_readiness():
    """Detailed dependency health check for GKE/Cloud Run availability."""
    from backend.main import readiness_check
    return await readiness_check()
