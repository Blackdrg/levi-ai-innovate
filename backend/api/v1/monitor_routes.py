"""
backend/api/v1/monitor_routes.py

Detailed Orchestrator & Decision Engine Monitoring.
Provides real-time transparency into LEVI's adaptive routing.
"""

import logging
import time
from fastapi import APIRouter, Depends
from backend.auth.logic import verify_admin
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.firebase import db as firestore_db

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

@router.get("/health/graph")
async def get_system_health_graph(is_admin: bool = Depends(verify_admin)):
    """
    v14.0 System Health Graph: Aggregates real-time stability metrics.
    """
    if not HAS_REDIS:
        return {"status": "degraded", "error": "Redis offline"}

    try:
        # 1. Resource Metrics (from vram_monitor.py)
        vram_free = int(redis_client.get("vram:live") or 0)
        vram_pressure = redis_client.get("vram:pressure") == "true"
        
        # 2. Performance Metrics
        redis_latency = float(redis_client.get("metrics:redis_latency_ms") or 0.0)
        neo4j_latency = float(redis_client.get("metrics:neo4j_latency_ms") or 0.0)
        
        # 3. Execution Metrics
        queue_depth = redis_client.llen("mission:queue") if redis_client.type("mission:queue") == "list" else 0
        failure_rate = float(redis_client.get("stats:failure_rate") or 0.0)
        
        # 4. Latency Distribution
        latencies = redis_client.lrange("metrics:latency_ms", 0, 99)
        avg_latency = 0
        if latencies:
            avg_latency = sum(int(l) for l in latencies) / len(latencies)

        return {
            "status": "online",
            "resources": {
                "vram_free_mb": vram_free,
                "vram_pressure": vram_pressure,
                "redis_latency_ms": redis_latency,
                "neo4j_latency_ms": neo4j_latency
            },
            "throughput": {
                "queue_depth": queue_depth,
                "mission_failure_rate": failure_rate,
                "avg_mission_latency_ms": round(avg_latency, 2)
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"[Monitor] Failed to collect health graph: {e}")
        return {"status": "error", "error": str(e)}
