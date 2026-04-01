"""
backend/api/analytics.py

System Analytics and Monitoring API - Real-time metrics and admin controls.
Refactored from backend/services/analytics/router.py.
"""

import logging
import os
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from backend.utils.exceptions import LEVIException
from backend.auth import verify_admin
from backend.firestore_db import db as firestore_db
from backend.utils.network import groq_breaker, together_breaker, CircuitBreaker
from backend.redis_client import r as redis_client, HAS_REDIS
from backend.utils.robustness import standard_retry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Analytics"])

@router.get("")
async def get_analytics_data(request: Request):
    """
    Returns high-level system analytics (chats, users, likes).
    """
    try:
        analytics_ref = firestore_db.collection("analytics")
        docs = analytics_ref.stream()
        
        total_chats = 0
        total_likes = 0
        total_users = 0
        
        for doc in docs:
            data = doc.to_dict()
            total_chats += data.get("chats_count", 0)
            total_likes += data.get("likes_count", 0)
            total_users += data.get("daily_users", 0)
            
        return {
            "total_chats": total_chats,
            "daily_users": total_users,
            "popular_topics": ["philosophy", "success", "wisdom", "stoicism"],
            "likes_count": total_likes,
            "status": "active",
            "environment": os.getenv("ENVIRONMENT", "production")
        }
    except Exception as e:
        logger.error(f"Analytics retrieval failed: {e}")
        raise LEVIException("Analytics sequence offline.", status_code=503)

@router.get("/admin/health")
async def admin_health_check(is_admin: bool = Depends(verify_admin)):
    """ Privileged health check. """
    return {"status": "ok", "admin": True, "timestamp": datetime.utcnow().isoformat()}

@router.get("/admin/breakers")
async def get_circuit_breakers(is_admin: bool = Depends(verify_admin)):
    """
    Returns the current state of system circuit breakers.
    """
    return {
        "groq": {
            "state": groq_breaker.state,
            "failures": groq_breaker.failures,
            "last_failure": groq_breaker.last_failure_time
        },
        "together": {
            "state": together_breaker.state,
            "failures": together_breaker.failures,
            "last_failure": together_breaker.last_failure_time
        }
    }

@router.post("/admin/breakers/{name}/{action}")
async def control_circuit_breaker(name: str, action: str, is_admin: bool = Depends(verify_admin)):
    """
    Manual override for system circuit breakers.
    """
    breaker: Optional[CircuitBreaker] = None
    if name == "groq": breaker = groq_breaker
    elif name == "together": breaker = together_breaker
    
    if not breaker:
        raise LEVIException("Circuit not found.", status_code=404)
        
    if action == "trip":
        breaker.state = "OPEN"
        breaker.failures = 10
    elif action == "reset":
        # Reset Logic
        breaker.on_success()
    else:
        raise LEVIException("Invalid action sequence.", status_code=400)
        
    return {"status": "success", "breaker": name, "new_state": breaker.state}

@router.get("/performance")
@router.get("/v2/performance")
async def get_performance_metrics(is_admin: bool = Depends(verify_admin)):
    """
    Returns live performance telemetry (p95 latency, error rate, instance count).
    """
    if not HAS_REDIS:
        return {"error": "Telemetry offline (Redis required).", "status": "degraded"}

    try:
        # 1. Latency p95
        latency_history = redis_client.lrange("metrics:latency_ms", 0, 99)
        durations = [int(d) for d in latency_history if d]
        p95 = np.percentile(durations, 95) if durations else 0
        
        # 2. Throughput
        total_requests = int(redis_client.get("metrics:total_requests") or 0)
        error_count = int(redis_client.get("metrics:error_count") or 0)
        
        # 3. Instance Registry
        instances = redis_client.hgetall("active_instances")
        instance_count = len(instances)

        # 4. Sovereign Monolith Metrics (v6.8)
        local_calls = int(redis_client.get("metrics:route:local") or 0)
        api_calls = int(redis_client.get("metrics:route:api") or 0)
        total_calls = local_calls + api_calls
        sov_ratio = (local_calls / total_calls * 100) if total_calls > 0 else 0

        # Memory Metrics
        faiss_hits = int(redis_client.get("metrics:memory:faiss_hit") or 0)
        memory_queries = int(redis_client.get("metrics:memory:total_queries") or 0)
        hit_rate = (faiss_hits / memory_queries * 100) if memory_queries > 0 else 0

        return {
            "p95_latency_ms": round(float(p95), 2),
            "total_requests": total_requests,
            "error_rate_percent": round((error_count / total_requests * 100), 2) if total_requests > 0 else 0,
            "active_instances": instance_count,
            "sovereign_ratio": f"{sov_ratio:.1f}%",
            "memory_metrics": {
                "faiss_hit_rate": f"{hit_rate:.1f}%",
                "active_context_size": int(redis_client.get("metrics:memory:active_kb") or 0)
            },
            "instance_details": {k.decode() if isinstance(k, bytes) else k: int(v) for k, v in instances.items()},
            "system_load": os.getloadavg() if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Metrics aggregation failed: {e}")
        raise LEVIException("Telemetry aggregation failed.", status_code=500)

@router.post("/track_share")
async def track_share():
    """ Tracks social sharing events. """
    from backend.firestore_db import update_analytics
    update_analytics("share_count")
    return {"status": "success"}

@router.post("/feedback")
async def submit_feedback(payload: dict):
    """
    Endpoint for user feedback on AI responses.
    """
    msg_id = payload.get("message_id")
    score = payload.get("score", 0.0)
    logger.info(f"Feedback Received [{msg_id}]: {score}")
    # Integration with Phase 4 Learning system here
    return {"status": "success", "message": "Feedback integrated into the field."}
