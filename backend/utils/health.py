import asyncio
import logging
import os
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def check_brain_health() -> Dict[str, Any]:
    """
    Sovereign Engine Probe: Performs an active self-diagnostic of the AI Brain.
    Checks Redis, Firestore, and AI service connectivity.
    """
    health = {
        "status": "hardened",
        "timestamp": time.time(),
        "checks": {
            "redis": False,
            "firestore": False,
            "local_llm": False,
            "groq_api": False,
            "tavily_api": False
        },
        "latency_ms": {}
    }

    # 1. Check Redis
    try:
        from backend.db.redis_client import r as redis_client
        start = time.time()
        if redis_client.ping():
            health["checks"]["redis"] = True
            health["latency_ms"]["redis"] = int((time.time() - start) * 1000)
    except Exception as e:
        logger.warning(f"[Probe] Redis unavailable: {e}")

    # 2. Check Firestore
    try:
        from backend.db.firestore_db import db as firestore_db
        start = time.time()
        # Simple doc read attempt
        firestore_db.collection("system").document("health_probe").get(timeout=2.0)
        health["checks"]["firestore"] = True
        health["latency_ms"]["firestore"] = int((time.time() - start) * 1000)
    except Exception as e:
        logger.warning(f"[Probe] Firestore unavailable: {e}")

    # 3. Check Local LLM Status
    try:
        from backend.services.orchestrator.local_engine import HAS_LLAMA_CPP, MODEL_PATH
        if HAS_LLAMA_CPP and os.path.exists(MODEL_PATH):
            health["checks"]["local_llm"] = True
    except Exception: pass

    # 4. Check AI API Circuit Breakers
    try:
        from backend.utils.network import groq_breaker, ai_service_breaker
        health["checks"]["groq_api"] = groq_breaker.state == "CLOSED"
        health["checks"]["tavily_api"] = ai_service_breaker.state == "CLOSED"
    except Exception: pass
    
    # 5. Check v13.0 Specifics (HNSW & Consensus)
    try:
        from backend.utils.vector_db import VectorDB
        from backend.agents.consensus_agent import ConsensusAgentV11
        import faiss
        
        # Check if HNSW is the active index type
        coll = await VectorDB.get_collection("global_health_check")
        health["checks"]["hnsw_index"] = isinstance(coll.index, faiss.IndexHNSWFlat)
        
        health["checks"]["consensus_agent"] = True # Profile active locally
    except Exception as e:
        logger.warning(f"[Probe] v13.0 Health Check failure: {e}")

    # Overall Status Mapping
    failed_counts = list(health["checks"].values()).count(False)
    if failed_counts > 2:
        health["status"] = "degraded"
    elif failed_counts > 0:
        health["status"] = "stable"
    
    return health
