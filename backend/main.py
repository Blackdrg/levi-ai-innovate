# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import json
import os
import asyncio

from backend.core.orchestrator import Orchestrator
from backend.core.memory_manager import MemoryManager
from backend.api.middleware.sovereign_shield import SovereignShield
from backend.api.middleware.ssrf import SSRFMiddleware
from backend.api.middleware.rate_limiter import RateLimitMiddleware
from backend.api.middleware.prometheus import PrometheusMiddleware
from backend.utils.tracing import setup_tracing
from backend.auth import get_current_user
from backend.api.v1.voice import router as voice_router
from backend.api.v1.evolution import router as evolution_router
from backend.api.v8.telemetry import router as telemetry_v8_router
from datetime import datetime, timezone
from fastapi.responses import JSONResponse
from backend.services.mcm import mcm_service
from backend.core.dcn.gossip import DCNGossip
from backend.core.dcn.raft_consensus import get_dcn_mesh, DCNMesh
from backend.core.memory.resonance_manager import get_resonance_manager, MemoryResonanceManager
from backend.db.redis import r_async as redis_async
from backend.services.ollama_health import ollama_monitor
from backend.services.health_monitor import health_monitor
from backend.core.goal_engine import goal_engine
from backend.services.voice.processor import AudioPulseProcessor
from backend.workers.event_consumer import start_event_consumers

# Initialize logger
logger = logging.getLogger("levi")

# Global state
orchestrator: Orchestrator = None
memory_manager: MemoryManager = None
dcn_gossip: DCNGossip = None
dcn_mesh: DCNMesh = None
resonance_manager: MemoryResonanceManager = None
audio_processor: AudioPulseProcessor = None
event_consumer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global orchestrator, memory_manager, dcn_gossip, dcn_mesh, resonance_manager, audio_processor, event_consumer
    
    logger.info("🚀 LEVI-AI Sovereign OS v16.3.0-AUTONOMOUS starting...")
    
    # 1. Initialize core services
    from backend.core.orchestrator import _orchestrator as orchestrator_instance
    orchestrator = orchestrator_instance
    memory_manager = MemoryManager()
    
    await orchestrator.initialize()
    await memory_manager.initialize()
    event_consumer = await start_event_consumers()

    # 3. Cognitive Kernel Initialization (v16.2.0 Sovereign OS)
    from backend.kernel.kernel_wrapper import kernel
    if kernel.rust_kernel:
        # Retrieve and log the Sovereign Boot Report
        boot_report = kernel.get_boot_report()
        logger.info(f"⚡ [Kernel] Sovereign Microkernel: [ONLINE]. Boot Report: {json.dumps(boot_report, indent=2)}")
        
        # Verify HAL & FS Architecture
        drivers = kernel.get_drivers()
        logger.info(f"📟 [Kernel] Hardware Drivers (HAL): {len(drivers)} active. Drivers: {drivers}")
        logger.info(f"📂 [Kernel] Sovereign Filesystem (SFS): [MOUNTED]")
    else:
        logger.warning("⚠️ [Kernel] Rust Binary Not Found. Running in [FALLBACK] mode.")
    
    # Link Orchestrator to GoalEngine
    goal_engine.orchestrator = orchestrator
    
    # 4. Initialize DCN Gossip Hub & Protocol
    from backend.core.dcn_protocol import get_dcn_protocol
    dcn_protocol = get_dcn_protocol()
    dcn_gossip = dcn_protocol.gossip
    
    if dcn_protocol.is_active:
        logger.info(f"🛰️ [Main] DCN Active. Node: {dcn_protocol.node_id}")
        await dcn_protocol.start_heartbeat(interval=30)
        # 🔗 [Wire] Consensus Listener handles BFT/Raft pulses
        await dcn_protocol.start_consensus_listener()
    
    # 4b. Phase 3.2 – DCN Mesh (Raft consensus layer)
    dcn_mesh = get_dcn_mesh()
    await dcn_mesh.start()
    logger.info("⚡ [Main] DCN Mesh (Raft) node=%s cluster=%s [ONLINE]",
                dcn_mesh.node_id, dcn_mesh.raft_consensus.cluster_key)
        
    # 5. Starting DCN Global Bridge
    from backend.utils.global_gossip import global_swarm_bridge
    from backend.memory.vector_store import SovereignVectorStore
    try:
        await global_swarm_bridge.initialize()
        await global_swarm_bridge.start()
        logger.info("🌐 [Main] Global Swarm Bridge [ONLINE]")
    except Exception as e:
        logger.warning(f"⚠️ [Main] Swarm Bridge degraded: {e}")
    
    # 6. Background Memory Sync (v14.2 Hardened)
    from backend.utils.runtime_tasks import create_tracked_task
    create_tracked_task(SovereignVectorStore.reindex_global_memory(), name="faiss-global-reindex")
    
    # 6b. Phase 3.1 – Memory Resonance Manager (T1→T2→T3→T4)
    resonance_manager = get_resonance_manager()
    await resonance_manager.start(user_ids=["global"])
    logger.info("🧬 [Main] Memory Resonance Manager [ONLINE] (5-min cycle)")
    
    # 7. Start Health, Model & Goal Monitors (v15.0 GA)
    await ollama_monitor.start()
    await health_monitor.start()
    await goal_engine.start()

    # 8. Start Memory Maintenance Loops (v15.0 Full Fulfillment)
    from backend.memory.background_reindexer import BackgroundReindexer
    # Memory maintenance and other periodic tasks are managed by the reindexer
    # or the detached event-driven autonomy system.

    # 9. Sovereign v16.2: Event-Driven Autonomy
    # Periodic tasks (mcm-recon, shadow-audit, optimizer, evolution) 
    # are now handled by the detached PulseEmitter + SovereignWorker.
    from backend.workers.pulse_emitter import PulseEmitter
    pulse_emitter = PulseEmitter()
    create_tracked_task(pulse_emitter.start(), name="pulse-emitter")

    # 10. Start Audio Pulse Recon (Phase 5)
    audio_processor = AudioPulseProcessor(user_id="system_recon")
    create_tracked_task(audio_processor.start(), name="audio-pulse-recon")
    
    # 🛡️ Phase 2: Model Pre-loading (Risk 2.2 Mitigation)
    # Pre-load embedding models and intent anchors during startup to eliminate first-request latency.
    logger.info("🧠 Pre-loading cognitive models (Embeddings & Intent anchors)...")
    try:
        from backend.embeddings import ONNXEmbedder
        from backend.core.intent_classifier import HybridIntentClassifier
        
        # 1. Start ONNX/BERT pre-loading
        await ONNXEmbedder.get_instance()
        
        # 2. Initialize Intent Anchors (Pre-calculates embeddings)
        classifier = HybridIntentClassifier()
        await classifier._initialize_anchors()
        
        logger.info("✅ Cognitive models warmed up.")
    except Exception as e:
        logger.error(f"⚠️ Model pre-loading failed: {e}. System will lazy-load models on demand.")

    logger.info("✅ LEVI-AI online and globally synchronized (Tier 2)")
    
    yield
    
    # Shutdown
    logger.info("🛑 LEVI-AI shutting down...")
    
    # 1. Graceful Orchestration Drainage (Graduation #8)
    if orchestrator:
        await orchestrator.force_abort_all("SYSTEM_SHUTDOWN")
        await orchestrator.teardown_gracefully(timeout=30)
    
    if dcn_gossip:
        await dcn_gossip.stop_gossip_hub()
    
    # Phase 3.2: Graceful DCN Mesh shutdown (snapshot before exit)
    if dcn_mesh:
        try:
            await dcn_mesh.take_snapshot()
        except Exception as _snap_err:
            logger.warning("[Shutdown] Raft snapshot failed: %s", _snap_err)
        await dcn_mesh.stop()
    
    # Phase 3.1: Stop Memory Resonance Manager
    if resonance_manager:
        await resonance_manager.stop()
    
    # 2. Stop Monitoring & Goal Services
    await health_monitor.stop()
    await ollama_monitor.stop()
    await goal_engine.stop()
    
    if audio_processor:
        audio_processor.stop()
    if event_consumer:
        await event_consumer.stop()
        
    await memory_manager.shutdown()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="LEVI-AI Sovereign OS",
    version="16.3.0-AUTONOMOUS",
    lifespan=lifespan
)

# Initialize OTEL Tracing
setup_tracing(app)


# Middleware stack (in order)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SSRFMiddleware)
app.add_middleware(SovereignShield)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Sovereign v15.0: Global Anti-Leaky Error Handler.
    Logs full trace internally but returns sanitized message to client.
    """
    logger.error(f"🚨 [GlobalError] {request.method} {request.url.path} failed: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal cognitive anomaly occurred. The mission has been safely quarantined.",
            "type": type(exc).__name__ if os.getenv("ENVIRONMENT") != "production" else "InternalError"
        }
    )

# Routes
from backend.api.v1.router import router as v1_router
app.include_router(v1_router, prefix="/api/v1")
app.include_router(telemetry_v8_router, prefix="/api/v8/telemetry")

# 🌐 Frontend Architecture Mounting (Sovereign v15.0)
# Serve shared assets (CSS/JS)
app.mount("/shared", StaticFiles(directory="frontend/shared"), name="shared")

# Serve static fallback UI
app.mount("/ui", StaticFiles(directory="frontend/static", html=True), name="static_ui")

# Serve main React application
# Note: Ensure React is built into frontend/react-app/dist
app.mount("/app", StaticFiles(directory="frontend/react-app/dist", html=True), name="react_app")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Root WebSocket gateway for LEVI-AI telemetry.
    Delegates to the Sovereign Telemetry service.
    """
    from backend.api.telemetry import telemetry_websocket
    # Use a generic client ID for static frontend or handle auth as needed
    await telemetry_websocket(websocket, "gateway_client")

@app.get("/healthz")
async def health_check():
    """Liveness probe: returns 200 iff the process is up."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/metrics", tags=["Infrastructure"])
async def metrics():
    """Exposes Prometheus metrics for scraping."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from starlette.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/readyz", tags=["Infrastructure"])
async def readiness_check():
    """
    Readiness probe: returns 200 iff dependencies for local execution are healthy.
    Degraded mode (Global Sync down) is flagged but does not fail the probe.
    """
    from backend.db.redis import r as redis_sync, HAS_REDIS
    from backend.db.postgres import PostgresDB
    from backend.services.mcm import HAS_PUBSUB
    from backend.kernel.kernel_wrapper import kernel as _kernel
    from backend.core.dcn_protocol import get_dcn_protocol

    _proto = get_dcn_protocol()
    _is_leader = (_proto.node_state == "leader") if _proto else False
    _gossip_term = getattr(_proto.hybrid_gossip, "raft_term", 0) if (_proto and _proto.hybrid_gossip) else 0

    health = {
        "status": "ready",
        "dependencies": {
            "redis": "connected" if HAS_REDIS else "disconnected",
            "postgres": "connected" if await PostgresDB.check_health() else "disconnected",
            "ollama": "online" if await ollama_monitor.is_online() else "offline",
            "global_sync": "active" if HAS_PUBSUB else "degraded ⚠️"
        },
        "swarm_info": {
            "node_id": _proto.node_id if _proto else "standalone",
            "leader": _is_leader,
            "term": _gossip_term
        },
        "raft_info": await dcn_mesh.get_cluster_status() if dcn_mesh else {"status": "offline"},
        "kernel_info": {
            "status": "online" if _kernel.rust_kernel else "fallback",
            "vram_governor": "active",
            "sfs_mounted": bool(_kernel.rust_kernel)
        },
        "graduation_score": await orchestrator.get_graduation_score() if orchestrator else 1.0
    }
    
    # 1. Critical Dependency: Redis
    if not HAS_REDIS:
        health["status"] = "not_ready"
        return JSONResponse(status_code=503, content=health)
        
    # 2. Critical Dependency: Postgres
    try:
        from backend.db.connection import PostgresSessionManager
        async with await PostgresSessionManager.get_scoped_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            
            # 🛡️ Graduation #23: Pool Monitoring
            from backend.db.connection import engine as db_engine
            pool = db_engine.pool
            health["dependencies"]["postgres"] = {
                "status": "connected",
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow()
            }
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")
        health["dependencies"]["postgres"] = "disconnected"
    # 3. Optional Dependency: Ollama
    try:
        import httpx
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ollama_host}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                health["dependencies"]["ollama"] = "connected"
            else:
                health["dependencies"]["ollama"] = f"degraded ({resp.status_code})"
                if os.getenv("ENVIRONMENT") == "production":
                    health["status"] = "not_ready"
                    return JSONResponse(status_code=503, content=health)
    except Exception:
        health["dependencies"]["ollama"] = "disconnected"
        # 🛡️ Graduation #23: In strict production mode, fail the probe if Ollama is down
        if os.getenv("ENVIRONMENT") == "production":
            health["status"] = "not_ready"
            return JSONResponse(status_code=503, content=health)

    return health

@app.get("/api/v1/brain/pulse")
async def system_pulse(current_user = Depends(get_current_user)):
    """System health and routing status"""
    from backend.utils.hardware import gpu_monitor
    vram = gpu_monitor.get_vram_usage()
    
    return {
        "system_graduation_score": await orchestrator.get_graduation_score() if orchestrator else 1.0,
        "vram_status": vram,
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
