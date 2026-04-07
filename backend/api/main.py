"""
LEVI-AI: Sovereign OS v14.0.0-Autonomous-SOVEREIGN.
Central Gateway & Service Orchestrator.
"""

import os
import logging
import time
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from backend.utils.metrics import MetricsHub

from backend.config.system import SOVEREIGN_VERSION, CLOUD_FALLBACK_ENABLED, CORS_ORIGINS

# Service Routers
from backend.api.v8.orchestrator import router as orchestrator_v1
from backend.api.v8.telemetry import router as telemetry_v1
from backend.core.dcn_protocol import DCNProtocol
from backend.api.v8.memory import router as memory_v1
from backend.api.v8.search import router as search_v1
from backend.api.v1.payments import router as payments_v1
from backend.api.v8.auth import router as auth_v1
from backend.api.billing import router as billing_v1
from backend.api.analytics import router as analytics_v1
from backend.api.agents import router as agents_v1
from backend.api.marketplace import router as marketplace_v1
from backend.api.compliance import router as compliance_v1
from backend.api.v8.learning import router as learning_v1
from backend.api.scheduling import router as scheduling_v1
from backend.api.v1.replay import router as replay_v1
from backend.api.v14.brain import router as brain_v14

# Middleware Tier
from backend.api.middleware.security_headers import SecurityHeadersMiddleware
from backend.api.middleware.rate_limiter import RateLimitMiddleware

# Core Logic
from backend.db.postgres_db import verify_resonance
from backend.db.partitions import ensure_audit_partitions
from backend.broadcast_utils import SovereignBroadcaster
from backend.core.model_router import ModelRouter

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Graduation Audit ---
    logger.info(f"🛡️ Validating LEVI-AI Stack Graduation ({SOVEREIGN_VERSION})...")
    logger.info(f"☁️ Cloud Fallback: {'ENABLED' if CLOUD_FALLBACK_ENABLED else 'DISABLED (Local-Only Mode)'}")
    
    try:
        from backend.db.postgres_db import verify_resonance
        from backend.db.partitions import ensure_audit_partitions
        if await verify_resonance():
            logger.info("✅ Database resonance confirmed. Local persistence active.")
            await ensure_audit_partitions()
        else:
            logger.warning("⚠️ Database sync drift detected.")
    except Exception as e:
        logger.error(f"❌ Startup Audit failed: {e}")

    # 🛡️ DCN Gossip Layer (v14.0.0-Autonomous)
    try:
        import asyncio
        from backend.core.dcn_protocol import DCNProtocol
        dcn = DCNProtocol()
        if dcn.is_active:
            # 1. Start Listener
            asyncio.create_task(dcn.start_listener(gossip_handler))
            
            # 2. Start Autonomous Heartbeat
            os.environ["NODE_ROLE"] = os.getenv("NODE_ROLE", "coordinator")
            asyncio.create_task(dcn.start_heartbeat(interval=30))
            logger.info(f"[DCN] Swarm Presence: [ESTABLISHED] Mode: {os.environ['NODE_ROLE']}")

            # 3. Start Distributed Worker Loop
            if os.getenv("DISTRIBUTED_MODE", "false").lower() == "true":
                from backend.core.executor.distributed import DistributedGraphExecutor
                from backend.db.redis import r_async as redis_client
                dist_executor = DistributedGraphExecutor(redis_client)
                asyncio.create_task(dist_executor.worker_loop())
                logger.info("[DCN] Distributed Worker Loop: [ACTIVE]")
    except Exception as e:
        logger.error(f"[DCN] Failed to initialize gossip/worker: {e}")
        
    yield
    # --- Shutdown logic if needed ---
    logger.info("🔌 Sovereign OS shutting down...")

app = FastAPI(
    title="LEVI-AI Distributed Stack",
    version=SOVEREIGN_VERSION,
    description="Sovereign AI Operating System (v14.0.0-Autonomous-SOVEREIGN Graduation)",
    lifespan=lifespan
)

# 1. Security Hardening (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1.5. Sovereign Security Hardening (Audit Prep)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit=100, window=60) # 100 RPM limit

# 2. Global Versioning & Telemetry Middleware
@app.middleware("http")
async def global_sovereign_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Process Request
    response = await call_next(request)
    
    # Inject Production Headers (RC1)
    response.headers["X-Sovereign-Version"] = SOVEREIGN_VERSION
    response.headers["X-Cloud-Fallback"] = str(CLOUD_FALLBACK_ENABLED).lower()
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Emit Telemetry Pulse
    SovereignBroadcaster.broadcast({
        "type": "TELEMETRY_PULSE",
        "path": request.url.path,
        "latency_ms": latency_ms,
        "status": response.status_code,
        "version": SOVEREIGN_VERSION,
        "ts": datetime.now(timezone.utc).isoformat()
    })
    return response

# 3. Service Router Registration
app.include_router(orchestrator_v1, prefix="/api/v1/orchestrator", tags=["Orchestration"])
app.include_router(telemetry_v1, prefix="/api/v1/telemetry", tags=["Telemetry"])
app.include_router(memory_v1, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(search_v1, prefix="/api/v1/search", tags=["Search"])
app.include_router(payments_v1, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(auth_v1, prefix="/api/v1/auth", tags=["Identity"])
app.include_router(billing_v1, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(analytics_v1, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(agents_v1, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(marketplace_v1, prefix="/api/v1/marketplace", tags=["Marketplace"])
app.include_router(compliance_v1, prefix="/api/v1/compliance", tags=["Compliance"])
app.include_router(scheduling_v1, prefix="/api/v1/scheduling", tags=["Scheduling"])
app.include_router(learning_v1, prefix="/api/v1/learning", tags=["Evolution"])
app.include_router(replay_v1, prefix="/api/v1/missions", tags=["Resilience"])
app.include_router(brain_v14, prefix="/api/v14", tags=["Brain Service v14.0"])

async def gossip_handler(pulse: Dict[str, Any]):
    """
    Sovereign DCN Gossip Handler (v2.0).
    Processes incoming pulses from the distributed cognitive network.
    """
    node = pulse.get("node")
    pulse_type = pulse.get("type")
    
    if pulse_type == "node_heartbeat":
        logger.debug(f"[DCN] Swarm Pulse: Node {node} is ACTIVE.")
    elif pulse_type == "cognitive_gossip":
        mission_id = pulse.get("payload", {}).get("mission_id")
        logger.info(f"[DCN] Cognitive Insight: {node} shared pulse for mission {mission_id}")
    else:
        logger.warning(f"[DCN] Unknown pulse received from {node}: {pulse_type}")


@app.get("/")
@app.get("/api/v1/health")
@app.get("/health")
async def health_status():
    """Official Pulse of the Distributed AI Stack."""
    return {
        "status": "online",
        "version": SOVEREIGN_VERSION,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "cloud_fallback": CLOUD_FALLBACK_ENABLED,
        "model_assignments": ModelRouter.get_all_assignments(),
        "resonance": "GRADUATED"
    }

@app.get("/api/v1/ready")
@app.get("/ready")
async def ready_status():
    """Surgical readiness probe for Docker/K8s."""
    from backend.db.redis import r_async as redis
    from backend.db.postgres_db import verify_resonance
    
    redis_alive = False
    try:
        await redis.ping()
        redis_alive = True
    except:
        pass
        
    db_alive = await verify_resonance()
    
    status = "ready" if redis_alive and db_alive else "degraded"
    
    return {
        "status": status,
        "redis": "connected" if redis_alive else "disconnected",
        "postgres": "resonant" if db_alive else "offline",
        "ts": datetime.now(timezone.utc).isoformat()
    }

# --- Prometheus Observability (v14.0) ---
@app.get("/metrics")
async def get_metrics():
    """Exposes real-time system and mission telemetry for Prometheus."""
    return Response(
        content=MetricsHub.get_latest_metrics(),
        media_type=MetricsHub.get_content_type()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
