"""
backend/api/monitor_routes.py

Detailed Orchestrator & Decision Engine Monitoring.
Provides real-time transparency into LEVI's adaptive routing.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from backend.services.auth.logic import verify_admin
from backend.db.redis_client import r as redis_client, HAS_REDIS
from backend.db.firestore_db import db as firestore_db
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/orchestrator", tags=["Monitoring"])

@router.get("/stats")
async def get_orchestrator_stats(is_admin: bool = Depends(verify_admin)):
    """
    Returns real-time statistics on decision routing, agent health, and optimization efficacy.
    """
    if not HAS_REDIS:
        return {"status": "degraded", "message": "Redis offline"}

    # 1. Route & Cache Efficacy
    routes = ["cache", "local", "tool", "api"]
    distribution = {r: int(redis_client.get(f"stats:route:{r}") or 0) for r in routes}
    
    # 2. Agent Health & Reliability (Phase 6 Hardening)
    from backend.core.tool_registry import _TOOL_INSTANCES
    from backend.db.redis_client import get_failure_count
    
    agent_health = {}
    for name in _TOOL_INSTANCES.keys():
        fail_count = get_failure_count(name)
        status = "healthy"
        if fail_count > 20: status = "degraded"
        if fail_count > 50: status = "critical"
        
        agent_health[name] = {
            "status": status,
            "failures_7d": fail_count
        }

    # 3. Decision Complexity & Performance
    complexity = {f"Level {i}": int(redis_client.get(f"stats:complexity:{i}") or 0) for i in range(4)}
    avg_cost = round(float(redis_client.get("stats:avg_cost_weight") or 0.0), 3)
    
    # 4. Evolution Status
    evolve_count = int(redis_client.get("system:evolution:interaction_count") or 0)
    
    from backend.services.learning.logic import get_learning_stats
    learning_stats = get_learning_stats()

    return {
        "status": "operational",
        "orchestration": {
            "routes": distribution,
            "complexity": complexity,
            "avg_cost_weight": avg_cost,
        },
        "agents": agent_health,
        "learning": learning_stats,
        "evolution": {
            "interaction_surplus": evolve_count,
            "threshold": 25
        }
    }

@router.get("/decisions")
async def get_recent_decisions(limit: int = 20, is_admin: bool = Depends(verify_admin)):
    """
    Fetches the latest decision audit logs from Firestore.
    """
    try:
        docs = (
            firestore_db.collection("decision_audit")
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit)
            .get()
        )
        decisions = [doc.to_dict() for doc in docs]
        return {"decisions": decisions}
    except Exception as e:
        logger.error(f"Failed to fetch decision logs: {e}")
        return {"decisions": [], "error": str(e)}

@router.get("/prompts")
async def get_prompt_performance(is_admin: bool = Depends(verify_admin)):
    """
    Returns the current score for all system instruction variants.
    """
    try:
        docs = firestore_db.collection("prompt_performance").get()
        prompts = [doc.to_dict() for doc in docs]
        return {"variants": prompts}
    except Exception as e:
        logger.error(f"Failed to fetch prompt stats: {e}")
        return {"variants": [], "error": str(e)}
