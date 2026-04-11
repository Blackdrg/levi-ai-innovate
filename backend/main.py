# backend/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import json

from backend.core.orchestrator import Orchestrator
from backend.core.memory_manager import MemoryManager
from backend.auth.middleware import SovereignShieldMiddleware
from backend.api.middleware.ssrf import SSRFMiddleware
from backend.api.middleware.rate_limiter import RateLimitMiddleware
from backend.api.middleware.prometheus import PrometheusMiddleware
from backend.utils.tracing import setup_tracing
from backend.auth import get_current_user
from backend.api.v1.voice import router as voice_router
from datetime import datetime, timezone
from fastapi.responses import JSONResponse
from backend.services.mcm import mcm_service
from backend.core.dcn.gossip import DCNGossip
from backend.db.redis import r_async as redis_async

# Initialize logger
logger = logging.getLogger("levi")

# Global state
orchestrator: Orchestrator = None
memory_manager: MemoryManager = None
dcn_gossip: DCNGossip = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global orchestrator, memory_manager, dcn_gossip
    
    logger.info("🚀 LEVI-AI Sovereign OS v14.2.0 starting...")
    
    # Initialize core services
    orchestrator = Orchestrator()
    memory_manager = MemoryManager()
    
    await orchestrator.initialize()
    await memory_manager.initialize()
    
    # 4. Initialize DCN Gossip Hub & Protocol
    from backend.core.dcn_protocol import DCNProtocol
    dcn_protocol = DCNProtocol()
    if dcn_protocol.is_active:
        await dcn_protocol.start_heartbeat(interval=30)
        # We also need a listener to handle incoming gossip
        async def dcn_handler(pulse):
            # 🛡️ Graduation #9: Global Abort Propagation
            if pulse.payload_type == "mission_aborted":
                from backend.utils.mission import MissionControl
                mission_id = pulse.mission_id
                reason = pulse.payload.get("reason", "Distributed abort pulse received.")
                logger.info(f"🚨 [DCN-Abort] Received global abort signal for {mission_id}. Reason: {reason}")
                MissionControl.cancel_mission(mission_id)
        await dcn_protocol.start_listener(dcn_handler)
    
    # 5. Starting DCN Global Bridge
    from backend.utils.global_gossip import global_swarm_bridge
    await global_swarm_bridge.initialize()
    await global_swarm_bridge.start()
    
    logger.info("✅ LEVI-AI online and globally synchronized")
    
    yield
    
    # Shutdown
    logger.info("🛑 LEVI-AI shutting down...")
    
    # 1. Graceful Orchestration Drainage (Graduation #8)
    if orchestrator:
        await orchestrator.teardown_gracefully(timeout=30)
    
    if dcn_gossip:
        await dcn_gossip.stop_gossip_hub()
    await memory_manager.shutdown()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="LEVI-AI Sovereign OS",
    version="14.2.0",
    lifespan=lifespan
)

# Initialize OTEL Tracing
setup_tracing(app)


# Middleware stack (in order)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SSRFMiddleware)
app.add_middleware(SovereignShieldMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
from backend.api.v1.router import router as v1_router
app.include_router(v1_router, prefix="/api/v1")

@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    """Liveness probe: returns 200 iff the process is up."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/readyz", tags=["Infrastructure"])
async def readiness_check():
    """
    Readiness probe: returns 200 iff dependencies for local execution are healthy.
    Degraded mode (Global Sync down) is flagged but does not fail the probe.
    """
    from backend.db.redis import r as redis_sync, HAS_REDIS
    from backend.db.postgres import PostgresDB
    from backend.services.mcm import HAS_PUBSUB
    
    health = {
        "status": "ready",
        "dependencies": {
            "redis": "connected" if HAS_REDIS else "disconnected",
            "postgres": "unknown",
            "global_sync": "active" if HAS_PUBSUB else "degraded ⚠️"
        },
        "swarm_info": {
            "node_id": dcn_gossip.node_id if "dcn_gossip" in globals() else "standalone",
            "coordinator": "active" if ("dcn_gossip" in globals() and dcn_gossip.is_coordinator) else "follower",
            "term": dcn_gossip.current_term if "dcn_gossip" in globals() else 0
        },
        "graduation_score": await orchestrator.get_graduation_score() if orchestrator else 0.0
    }
    
    # 1. Critical Dependency: Redis
    if not HAS_REDIS:
        health["status"] = "not_ready"
        return JSONResponse(status_code=503, content=health)
        
    # 2. Critical Dependency: Postgres
    try:
        async with PostgresDB._session_factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            health["dependencies"]["postgres"] = "connected"
    except Exception:
        health["dependencies"]["postgres"] = "disconnected"
        health["status"] = "not_ready"
        return JSONResponse(status_code=503, content=health)

    return health

@app.get("/api/v1/brain/pulse")
async def system_pulse(current_user = Depends(get_current_user)):
    """System health and routing status"""
    return {
        "system_graduation_score": await orchestrator.get_graduation_score() if orchestrator else 1.0,
        "vram_pressure": await orchestrator.check_vram_pressure() if orchestrator else 0.0,
        "active_missions": await orchestrator.count_active_missions() if orchestrator else 0,
        "dcn_health": await orchestrator.get_dcn_health() if orchestrator else "offline"
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Keep internal task handler for GCP webhook orchestration
@app.post("/api/v1/internal/tasks/mission_handler")
async def cloud_tasks_mission_handler(request: dict):
    """
    Sovereign v14.1.0: Cloud Tasks Secure Webhook.
    Handles background mission execution triggered by GCP.
    """
    from backend.tasks import execute_mission_from_cloud_task
    
    mission_id = request.get("mission_id")
    payload = request.get("payload", {})
    
    if not mission_id or not payload:
        raise HTTPException(status_code=400, detail="Invalid mission payload")
        
    logger.info(f"📥 [InternalTask] Received Cloud Task trigger for mission: {mission_id}")
    success = await execute_mission_from_cloud_task(mission_id, payload)
    
    if not success:
        raise HTTPException(status_code=500, detail="Execution failed")
        
    return {"status": "success", "mission_id": mission_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
