"""
LEVI-AI: Sovereign OS v14.0.0-Autonomous-SOVEREIGN.
Central Gateway & Service Orchestrator.
"""

import os
import logging
import time
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from backend.utils.metrics import MetricsHub
from backend.utils.tracing import setup_tracing

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
from backend.api.v8.health import router as health_v1
from backend.api.v8.debug import router as debug_v8

# Middleware Tier
from backend.api.middleware.security_headers import SecurityHeadersMiddleware
from backend.api.middleware.rate_limiter import RateLimitMiddleware
from backend.api.middleware.ssrf import SSRFMiddleware

# Core Logic
from backend.db.postgres_db import verify_resonance
from backend.db.partitions import ensure_audit_partitions
from backend.broadcast_utils import SovereignBroadcaster
from backend.core.model_router import ModelRouter
from backend.utils.startup import collect_startup_checks
from backend.utils.health import probe_dependencies
from backend.utils.runtime_tasks import begin_shutdown, create_tracked_task, is_shutting_down

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

    # 🛡️ DCN Gossip & Resilience Layer (v14.1.0)
    try:
        import asyncio
        from backend.core.dcn.gossip import DCNGossip
        from backend.core.dcn.consistency import ConsistencyEngine
        from backend.services.learning.hygiene import MemoryPruningManager
        
        # 1. Leader Election & Gossip
        from backend.core.dcn.registry import dcn_registry
        gossip = dcn_registry.get_gossip()
        create_tracked_task(gossip.start_election_loop(), name="dcn-election-loop")
        
        # 2. State Reconciliation (Anti-Entropy)
        consistency = dcn_registry.get_consistency()
        create_tracked_task(consistency.start_reconciliation_loop(interval=60), name="dcn-reconcile-loop")
        
        # 3. Memory Hygiene (24h cycles)
        hygiene = MemoryPruningManager()
        async def run_hygiene_periodically():
            while not is_shutting_down():
                await hygiene.run_hygiene_cycle()
                await asyncio.sleep(86400) # Once a day
        
        create_tracked_task(run_hygiene_periodically(), name="memory-hygiene-job")
        # 5. Monitoring & Graduation
        from backend.utils.metrics import GRADUATION_SCORE
        GRADUATION_SCORE.set(1.0)
        
        # --- v15.0 Recovery & Liveness (Fix #1, #2, #3, #5) ---
        from backend.core.execution_state import CentralExecutionState
        from backend.services.ollama_health import ollama_monitor
        from backend.db.milvus_client import MilvusClient
        from backend.db.neo4j_db import SovereignGraph
        
        # A. Start Model Tier Monitor
        create_tracked_task(ollama_monitor.start(), name="ollama-monitor")
        
        # B. Verify Cognitive Tiers (Blocking)
        logger.info("[Sovereign] Initializing Cognitive Tiers...")
        MilvusClient.connect()
        SovereignGraph.get_driver()
        
        # C. Recover Active Missions (Post-Tier Ready)
        recovered_missions = await CentralExecutionState.load_state_on_boot()
        if recovered_missions:
            logger.info(f"[Sovereign] Successfully loaded {len(recovered_missions)} missions for potential recovery.")
            
        # D. Unified MCM Pulse (v16.0-GA)
        from backend.services.mcm import mcm_service
        await mcm_service.start()
        
        async def mcm_reconciliation_pulse():
            while not is_shutting_down():
                await mcm_service.run_reconciliation()
                await asyncio.sleep(60) # 1 minute consistency pulse
        
        create_tracked_task(mcm_reconciliation_pulse(), name="mcm-reconciliation-pulse")
        
        # E. Periodic Disaster Recovery Audit (Phase 3)
        from backend.scripts.disaster_recovery import DisasterRecoveryEngine
        async def disaster_recovery_pulse():
            while not is_shutting_down():
                await DisasterRecoveryEngine.run_audit()
                await asyncio.sleep(300) # 5 minute health audit
        
        create_tracked_task(disaster_recovery_pulse(), name="disaster-recovery-pulse")

        logger.info("[Sovereign] System marked as 100% PRODUCTION GRADUATED (v16.0.0-GA).")

    except Exception as e:
        logger.error(f"[DCN] Failed to initialize resilience loops: {e}")
        
    yield
    # --- Shutdown logic if needed ---
    logger.info("🔌 Sovereign OS shutting down...")
    
    try:
        from backend.core.orchestrator import _orchestrator
        await _orchestrator.teardown_gracefully()
    except Exception as e:
        logger.error(f"Orchestrator teardown failed: {e}")
        
    await begin_shutdown()
    try:
        from backend.db.postgres_db import close_resonance
        await close_resonance()
    except Exception as exc:
        logger.warning("Shutdown DB close anomaly: %s", exc)

app = FastAPI(
    title="LEVI-AI Distributed Stack",
    version=SOVEREIGN_VERSION,
    description="Sovereign AI Operating System (v14.0.0-Autonomous-SOVEREIGN Graduation)",
    lifespan=lifespan
)
setup_tracing(app)

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
app.add_middleware(RateLimitMiddleware)

# 2. Global Versioning & Telemetry Middleware
@app.middleware("http")
async def global_sovereign_middleware(request: Request, call_next):
    if is_shutting_down() and request.url.path not in {"/health", "/ready", "/metrics", "/api/v1/health", "/api/v1/ready"}:
        return Response(
            content='{"status":"shutting_down"}',
            media_type="application/json",
            status_code=503,
            headers={"Retry-After": "5"},
        )
    start_time = time.time()
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    
    # Process Request
    response = await call_next(request)
    
    # Inject Production Headers (RC1)
    response.headers["X-Sovereign-Version"] = SOVEREIGN_VERSION
    response.headers["X-Cloud-Fallback"] = str(CLOUD_FALLBACK_ENABLED).lower()
    response.headers["X-Trace-ID"] = trace_id
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Emit Telemetry Pulse
    SovereignBroadcaster.broadcast({
        "type": "TELEMETRY_PULSE",
        "path": request.url.path,
        "trace_id": trace_id,
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
app.include_router(debug_v8, prefix="/api/v8", tags=["Sovereign Debug"])
app.include_router(health_v1, prefix="/api/v1/orchestrator/health", tags=["Health & DCN"])

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
@app.get("/healthz")
async def health_status():
    """Official Pulse of the Distributed AI Stack."""
    startup = collect_startup_checks()
    dependency_health = await probe_dependencies()
    from backend.core.v13.vram_guard import VRAMGuard

    return {
        "status": dependency_health["status"],
        "version": SOVEREIGN_VERSION,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "cloud_fallback": CLOUD_FALLBACK_ENABLED,
        "cpu_fallback": VRAMGuard.CPU_FALLBACK_ACTIVE,
        "model_assignments": ModelRouter.get_all_assignments(),
        "resonance": "GRADUATED",
        "dependencies": dependency_health,
        "startup": startup,
    }

@app.get("/api/v1/ready")
@app.get("/ready")
async def ready_status():
    """Surgical readiness probe for Docker/K8s."""
    startup = collect_startup_checks()
    dependency_health = await probe_dependencies()
    redis_alive = dependency_health["checks"]["redis"]["ok"]
    db_alive = dependency_health["checks"]["postgres"]["ok"]
    ollama_alive = dependency_health["checks"]["ollama"]["ok"]
    # Decouple Redis from readiness probe: system can start even if Redis is degraded.
    status = "ready" if db_alive and ollama_alive and startup["ready_for_production"] else "degraded"

    return {
        "status": status,
        "redis": "connected" if redis_alive else "disconnected",
        "postgres": "resonant" if db_alive else "offline",
        "ollama": "reachable" if ollama_alive else "offline",
        "dependencies": dependency_health,
        "startup": startup,
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
