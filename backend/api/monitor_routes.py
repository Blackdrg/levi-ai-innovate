"""
backend/api/monitor_routes.py

Detailed Orchestrator & Decision Engine Monitoring.
Provides real-time transparency into LEVI's adaptive routing.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from backend.auth import verify_admin
from backend.redis_client import r as redis_client, HAS_REDIS
from backend.firestore_db import db as firestore_db
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/orchestrator", tags=["Monitoring"])

@router.get("/stats")
async def get_orchestrator_stats(is_admin: bool = Depends(verify_admin)):
    """
    Returns real-time statistics on decision routing and complexity.
    """
    if not HAS_REDIS:
        return {"status": "degraded", "message": "Redis offline"}

    # 1. Route Distribution
    routes = ["cache", "local", "tool", "api"]
    distribution = {}
    for r in routes:
        count = int(redis_client.get(f"stats:route:{r}") or 0)
        distribution[r] = count

    # 2. Complexity Spreading
    complexity = {}
    for i in range(4):
        count = int(redis_client.get(f"stats:complexity:{i}") or 0)
        complexity[f"Level {i}"] = count

    # 3. Cost & Latency (Averages)
    avg_cost = float(redis_client.get("stats:avg_cost_weight") or 0.0)
    avg_latency = float(redis_client.get("stats:avg_latency_ms") or 0.0)

    # 4. Evolver Status
    evolve_count = int(redis_client.get("system:evolution:interaction_count") or 0)

    return {
        "health": "ok",
        "evolution_state": evolution_state.value,
        "performance": {
            "avg_confidence": round(avg_conf * 100, 1),
            "avg_quality": round(avg_rating, 2),
            "is_critical": evolution_state == EvolutionState.CRITICAL
        },
        "learning": learning_stats,
        "orchestration": {
            "avg_cost_weight": round(float(redis_client.get("stats:avg_cost_weight") or 0.0), 3),
            "route_distribution": {
                "local": int(redis_client.get("stats:route:local") or 0),
                "api": int(redis_client.get("stats:route:api") or 0),
                "cache": int(redis_client.get("stats:route:cache") or 0)
            }
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
