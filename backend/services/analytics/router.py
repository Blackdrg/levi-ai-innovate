from fastapi import APIRouter, Depends, HTTPException, Request # type: ignore
from typing import Optional
import numpy as np
import os
from datetime import datetime
import json
import logging

from backend.auth import verify_admin # type: ignore
from backend.firestore_db import db as firestore_db # type: ignore
from backend.circuit_breaker import groq_breaker, together_breaker, CircuitBreaker # type: ignore
from backend.redis_client import r as redis_client, HAS_REDIS # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Analytics"])

@router.get("")
async def get_analytics_data(request: Request):
    try:
        # Check from analytics collection
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
        raise HTTPException(status_code=503, detail="Analytics temporarily unavailable")

@router.get("/admin/health")
async def admin_health_check(is_admin: bool = Depends(verify_admin)):
    return {"status": "ok", "admin": True}

@router.get("/admin/breakers")
async def get_circuit_breakers(is_admin: bool = Depends(verify_admin)):
    """
    Diagnostic endpoint to view the state of all global circuit breakers.
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
    """Manual override for circuit breakers."""
    breaker: Optional[CircuitBreaker] = None
    if name == "groq": breaker = groq_breaker
    elif name == "together": breaker = together_breaker
    
    if not breaker:
        raise HTTPException(status_code=404, detail="Breaker not found")
        
    if action == "trip":
        breaker.state = "OPEN"
        breaker.failures = 10
    elif action == "reset":
        breaker.state = "CLOSED"
        breaker.failures = 0
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    return {"status": "success", "breaker": name, "new_state": breaker.state}

@router.get("/v2/performance")
async def get_performance_metrics(is_admin: bool = Depends(verify_admin)):
    """
    Phase 45: Live High-fidelity performance metrics.
    Aggregates latency p95 and throughput from Redis.
    """
    if not HAS_REDIS:
        return {"error": "Redis unavailable for live metrics", "status": "degraded"}

    try:
        # Aggregation Logic
        latency_history = redis_client.lrange("metrics:latency_ms", 0, 99)
        durations = [int(d) for d in latency_history if d]
        
        p95 = np.percentile(durations, 95) if durations else 0
        total_requests = int(redis_client.get("metrics:total_requests") or 0)
        error_count = int(redis_client.get("metrics:error_count") or 0)
        
        # Instance count from Phase 41 registry
        instances = redis_client.hgetall("active_instances")
        instance_count = len(instances)

        return {
            "p95_latency_ms": round(float(p95), 2),
            "total_requests": total_requests,
            "error_rate_percent": round((error_count / total_requests * 100), 2) if total_requests > 0 else 0,
            "active_instances": instance_count,
            "instance_details": {k.decode() if isinstance(k, bytes) else k: int(v) for k, v in instances.items()},
            "system_load": os.getloadavg() if hasattr(os, "getloadavg") else [0.1, 0.2, 0.1],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Live performance aggregation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_feedback(payload: dict):
    """Phase 43: Feedback endpoint for LLM response evaluation."""
    msg_id = payload.get("message_id")
    score = payload.get("score", 0.0)
    logger.info(f"Feedback received for {msg_id}: {score}")
    # In production, we'd store this in Firestore for training
    return {"status": "success"}

@router.post("/track_share")
async def track_share():
    """Phase 43: Track social sharing events."""
    from backend.firestore_db import update_analytics # type: ignore
    update_analytics("share_count")
    return {"status": "success"}
