# backend/main.py
"""
LEVI-AI Sovereign OS v22.0.0 — FastAPI application entrypoint.

Startup sequence (lifespan):
  1. Orchestrator boot (hardware calibration, DCN, sentinel).
  2. Kernel binary check & telemetry start.
  3. DCN protocol & Raft mesh.
  4. Memory resonance manager.
  5. Health monitors (Ollama, system health).
  6. Cognitive model warm-up (ONNX embeddings, intent anchors).
  7. Event-driven autonomy (PulseEmitter).
  8. Background infrastructure (audio, secret rotation, DR, discovery).

Shutdown sequence:
  1. Force-abort active missions.
  2. Drain orchestrator with 30 s timeout.
  3. Stop DCN gossip, Raft mesh, memory resonance.
  4. Stop health monitors, goal engine.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import json
import os
import asyncio
import subprocess
from datetime import datetime, timezone

from fastapi.responses import JSONResponse

# ── Logging must be configured before anything else ───────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("levi")

# ── Global state ──────────────────────────────────────────────────────────────
from backend.core.orchestrator import orchestrator, _orchestrator
from backend.services.memory_manager import MemoryManager

memory_manager   = None
dcn_gossip       = None
dcn_mesh         = None
resonance_manager = None
audio_processor  = None
event_consumer   = None

# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory_manager, dcn_gossip, dcn_mesh, resonance_manager, audio_processor, event_consumer

    logger.info("🚀 LEVI-AI Sovereign OS v22.0.0 starting...")

    from backend.utils.runtime_tasks import create_tracked_task

    # ── 0. Rust Core Runtime Wakeup ────────────────────────────────────────────
    try:
        logger.info("⚡ [Native] Awakening LEVI Core Runtime (Rust)...")
        runtime_path = os.path.join(os.getcwd(), "backend", "levi_runtime")
        # Run 'cargo run' in a background process
        runtime_proc = subprocess.Popen(
            ["cargo", "run", "--release"], 
            cwd=runtime_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info("✅ [Native] Core Runtime process spawned (PID: %d)", runtime_proc.pid)
    except Exception as exc:
        logger.error("⚠️  [Native] Failed to spawn Rust runtime: %s", exc)

    # ── 1. Orchestrator boot ──────────────────────────────────────────────────
    memory_manager = MemoryManager()
    await orchestrator.initialize()
    await memory_manager.initialize()

    # ── 2. Event consumers ────────────────────────────────────────────────────
    from backend.workers.event_consumer import start_event_consumers
    event_consumer = await start_event_consumers()

    # ── 3. Kernel telemetry & Serial Bridge ────────────────────────────────────
    from backend.kernel.kernel_wrapper import kernel
    from backend.kernel.serial_bridge import kernel_bridge
    
    if kernel.rust_kernel:
        boot_report = kernel.get_boot_report()
        logger.info("⚡ [Kernel] ONLINE. Boot report: %s", json.dumps(boot_report, indent=2))
        drivers = kernel.get_drivers()
        logger.info("📟 [Kernel] HAL drivers: %d active.", len(drivers))
    else:
        logger.warning("⚠️  [Kernel] Binary not compiled — Python fallback mode.")
    
    # Start the serial-to-event-bus bridge
    await kernel_bridge.start()
    kernel.start_background_tasks()

    # ── 4. Goal engine linkage ────────────────────────────────────────────────
    from backend.core.goal_engine import goal_engine
    goal_engine.orchestrator = orchestrator

    # ── 5. DCN protocol + Raft mesh ───────────────────────────────────────────
    from backend.core.dcn_protocol import get_dcn_protocol
    dcn_protocol = get_dcn_protocol()
    dcn_gossip   = getattr(dcn_protocol, "gossip", None)

    if getattr(dcn_protocol, "is_active", False):
        logger.info("🛰️  [DCN] Active. Node: %s", dcn_protocol.node_id)
        await dcn_protocol.start_heartbeat(interval=30)
        await dcn_protocol.start_consensus_listener()

    from backend.core.dcn.raft_consensus import get_dcn_mesh
    dcn_mesh = get_dcn_mesh()
    await dcn_mesh.start()
    logger.info("⚡ [Mesh] Raft node=%s cluster=%s ONLINE",
                dcn_mesh.node_id,
                getattr(dcn_mesh.raft_consensus, "cluster_key", "N/A"))

    # gRPC P2P gossip server
    try:
        from backend.dcn.grpc_server import serve_gossip_service
        grpc_port = int(os.getenv("DCN_GRPC_PORT", "9000"))
        create_tracked_task(serve_gossip_service(dcn_protocol, port=grpc_port), name="dcn-grpc-server")
        if getattr(dcn_protocol, "hybrid_gossip", None):
            interval = int(os.getenv("DCN_GOSSIP_INTERVAL", "30"))
            create_tracked_task(dcn_protocol.hybrid_gossip.start_discovery_loop(interval=interval),
                                name="dcn-hybrid-gossip")
    except Exception as exc:
        logger.warning("⚠️  [DCN] gRPC server degraded: %s", exc)

    # ── 6. Global swarm bridge ────────────────────────────────────────────────
    try:
        from backend.utils.global_gossip import global_swarm_bridge
        await global_swarm_bridge.initialize()
        await global_swarm_bridge.start()
        logger.info("🌐 [Swarm] Bridge ONLINE")
    except Exception as exc:
        logger.warning("⚠️  [Swarm] Bridge degraded: %s", exc)

    # ── 7. FAISS global reindex ───────────────────────────────────────────────
    try:
        from backend.memory.vector_store import SovereignVectorStore
        create_tracked_task(SovereignVectorStore.reindex_global_memory(), name="faiss-global-reindex")
    except Exception as exc:
        logger.warning("⚠️  [VectorStore] Reindex skipped: %s", exc)

    # ── 8. Memory resonance manager ───────────────────────────────────────────
    from backend.core.memory.resonance_manager import get_resonance_manager
    resonance_manager = get_resonance_manager()
    await resonance_manager.start(user_ids=["global"])
    logger.info("🧬 [Resonance] Manager ONLINE (5-min cycle)")

    # ── 9. Health & goal monitors ─────────────────────────────────────────────
    from backend.services.ollama_health import ollama_monitor
    from backend.services.health_monitor import health_monitor
    await ollama_monitor.start()
    await health_monitor.start()
    await goal_engine.start()

    # ── 10. PulseEmitter (event-driven autonomy) ──────────────────────────────
    from backend.workers.pulse_emitter import PulseEmitter
    create_tracked_task(PulseEmitter().start(), name="pulse-emitter")

    # ── 11. Audio pulse recon ─────────────────────────────────────────────────
    try:
        from backend.services.voice.processor import AudioPulseProcessor
        audio_processor = AudioPulseProcessor(user_id="system_recon")
        create_tracked_task(audio_processor.start(), name="audio-pulse-recon")
    except Exception as exc:
        logger.warning("⚠️  [Audio] Processor skipped: %s", exc)

    # ── 12. Graduation services ───────────────────────────────────────────────
    try:
        from backend.services.discovery import service_discovery
        from backend.services.dr_manager import dr_manager
        from backend.services.secret_rotator import secret_rotator
        create_tracked_task(service_discovery.start_heartbeat_loop(), name="service-discovery")
        create_tracked_task(dr_manager.check_regional_health(), name="dr-check")
        create_tracked_task(secret_rotator.check_and_rotate(), name="secret-rotate")
    except Exception as exc:
        logger.warning("⚠️  [Services] Graduation services partially degraded: %s", exc)

    if os.getenv("ENABLE_CHAOS") == "true":
        try:
            from backend.services.chaos_testing import chaos_agent
            create_tracked_task(chaos_agent.start_chaos_simulation(), name="chaos-agent")
        except Exception:
            pass

    # ── 13. Cognitive model warm-up ───────────────────────────────────────────
    logger.info("🧠 Pre-loading cognitive models...")
    try:
        from backend.embeddings import ONNXEmbedder
        from backend.core.intent_classifier import HybridIntentClassifier
        await ONNXEmbedder.get_instance()
        classifier = HybridIntentClassifier()
        await classifier._initialize_anchors()
        logger.info("✅ Cognitive models warmed up.")
    except Exception as exc:
        logger.error("⚠️  Model pre-loading failed: %s — will lazy-load.", exc)

    logger.info("✅ LEVI-AI v22.0.0 ONLINE")

    yield  # ← app is running here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("🛑 LEVI-AI shutting down...")

    await orchestrator.force_abort_all("SYSTEM_SHUTDOWN")
    await orchestrator.teardown_gracefully(timeout=30)

    if dcn_gossip:
        try:
            await dcn_gossip.stop_gossip_hub()
        except Exception:
            pass

    if dcn_mesh:
        try:
            await dcn_mesh.take_snapshot()
        except Exception as exc:
            logger.warning("[Shutdown] Raft snapshot failed: %s", exc)
        await dcn_mesh.stop()

    if resonance_manager:
        await resonance_manager.stop()

    from backend.services.ollama_health import ollama_monitor
    from backend.services.health_monitor import health_monitor
    await health_monitor.stop()
    await ollama_monitor.stop()
    await goal_engine.stop()

    if audio_processor:
        audio_processor.stop()
    if event_consumer:
        await event_consumer.stop()

    await memory_manager.shutdown()
    logger.info("✅ Shutdown complete.")


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="LEVI-AI Sovereign OS",
    version="22.0.0-SOVEREIGN",
    lifespan=lifespan,
)

# ── Tracing ────────────────────────────────────────────────────────────────────
from backend.utils.tracing import setup_tracing
setup_tracing(app)

# ── Middleware (inner → outer, so outer runs first) ───────────────────────────
from backend.api.middleware.sovereign_shield import SovereignShield
from backend.api.middleware.ssrf import SSRFMiddleware
from backend.api.middleware.rate_limiter import RateLimitMiddleware
from backend.api.middleware.prometheus import PrometheusMiddleware

app.add_middleware(PrometheusMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SSRFMiddleware)
app.add_middleware(SovereignShield)

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global error handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def _global_error_handler(request: Request, exc: Exception):
    logger.error("🚨 [GlobalError] %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "status":  "error",
            "message": "An internal anomaly occurred. Mission safely quarantined.",
            "type":    type(exc).__name__ if os.getenv("ENVIRONMENT") != "production" else "InternalError",
        },
    )

# ── Routers ───────────────────────────────────────────────────────────────────

from backend.api.v1.router import router as v1_router
from backend.api.v1.voice import router as voice_router
from backend.api.v1.evolution import router as evolution_router
from backend.api.v8.telemetry import router as telemetry_v8_router

app.include_router(v1_router,          prefix="/api/v1")
app.include_router(voice_router,       prefix="/api/v1/voice")
app.include_router(evolution_router,   prefix="/api/v1/evolution")
app.include_router(telemetry_v8_router, prefix="/api/v8/telemetry")

# ── Static file serving ───────────────────────────────────────────────────────

def _mount_if_exists(path: str, directory: str, name: str, html: bool = False):
    if os.path.isdir(directory):
        app.mount(path, StaticFiles(directory=directory, html=html), name=name)

_mount_if_exists("/shared", "frontend/shared",            name="shared")
_mount_if_exists("/ui",     "frontend/static",            name="static_ui",  html=True)
_mount_if_exists("/app",    "frontend/react-app/dist",    name="react_app",  html=True)
_mount_if_exists("/levi",   "levi-frontend/dist",         name="levi_app",   html=True)

# ── Core endpoints ────────────────────────────────────────────────────────────

from backend.auth import get_current_user

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    from backend.api.telemetry import telemetry_websocket
    await telemetry_websocket(websocket, "gateway_client")


@app.websocket("/ws/telemetry")
async def telemetry_websocket_endpoint(websocket: WebSocket):
    from backend.api.telemetry import telemetry_websocket_kernel
    await telemetry_websocket_kernel(websocket)


@app.get("/healthz", tags=["Infrastructure"])
async def health_check():
    """Liveness probe."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/readyz", tags=["Infrastructure"])
async def readiness_check():
    """Readiness probe — checks Redis, Postgres, Ollama."""
    from backend.db.redis import HAS_REDIS
    from backend.db.postgres import PostgresDB
    from backend.services.mcm import HAS_PUBSUB
    from backend.kernel.kernel_wrapper import kernel as _kernel
    from backend.core.dcn_protocol import get_dcn_protocol

    _proto    = get_dcn_protocol()
    _leader   = (getattr(_proto, "node_state", None) == "leader") if _proto else False
    _term     = getattr(getattr(_proto, "hybrid_gossip", None), "raft_term", 0) if _proto else 0

    health = {
        "status": "ready",
        "os":     "v22.0.0-SOVEREIGN",
        "dependencies": {
            "redis":       "connected" if HAS_REDIS else "disconnected",
            "postgres":    "connected" if await PostgresDB.check_health() else "disconnected",
            "ollama":      "unknown",
            "global_sync": "active" if HAS_PUBSUB else "degraded",
            "native_core": "online" if await rust_bridge.check_health() else "disconnected",
        },

        "swarm": {
            "node_id": _proto.node_id if _proto else "standalone",
            "leader":  _leader,
            "term":    _term,
        },
        "raft":   await dcn_mesh.get_cluster_status() if dcn_mesh else {"status": "offline"},
        "kernel": {
            "status":       "online" if _kernel.rust_kernel else "fallback",
            "sfs_mounted":  bool(_kernel.rust_kernel),
        },
        "graduation": await orchestrator.get_graduation_score() if orchestrator else 1.0,
    }

    if not HAS_REDIS:
        health["status"] = "not_ready"
        return JSONResponse(status_code=503, content=health)

    # Postgres deep check
    try:
        from backend.db.connection import PostgresSessionManager, engine as db_engine
        from sqlalchemy import text
        async with await PostgresSessionManager.get_scoped_session() as session:
            await session.execute(text("SELECT 1"))
        pool = db_engine.pool
        health["dependencies"]["postgres"] = {
            "status":     "connected",
            "pool_size":  pool.size(),
            "checked_out": pool.checkedout(),
            "overflow":   pool.overflow(),
        }
    except Exception as exc:
        logger.error("Postgres health check failed: %s", exc)
        health["dependencies"]["postgres"] = "disconnected"

    # Ollama check
    try:
        import httpx
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ollama_host}/api/tags", timeout=2.0)
        health["dependencies"]["ollama"] = "connected" if resp.status_code == 200 else f"degraded ({resp.status_code})"
        if resp.status_code != 200 and os.getenv("ENVIRONMENT") == "production":
            health["status"] = "not_ready"
            return JSONResponse(status_code=503, content=health)
    except Exception:
        health["dependencies"]["ollama"] = "disconnected"
        if os.getenv("ENVIRONMENT") == "production":
            health["status"] = "not_ready"
            return JSONResponse(status_code=503, content=health)

    return health


@app.get("/api/v1/brain/pulse", tags=["Brain"])
async def system_pulse(current_user=Depends(get_current_user)):
    """System health and routing status."""
    from backend.utils.hardware import gpu_monitor
    return {
        "graduation_score": await orchestrator.get_graduation_score() if orchestrator else 1.0,
        "vram_pressure":    await orchestrator.get_vram_pressure()    if orchestrator else 0.0,
        "active_missions":  await orchestrator.count_active_missions() if orchestrator else 0,
        "dcn_health":       await orchestrator.get_dcn_health()        if orchestrator else "offline",
        "native_cluster":   await rust_bridge.check_health(),
        "gpu":              gpu_monitor.get_vram_usage(),
    }



@app.get("/metrics", tags=["Infrastructure"])
async def prometheus_metrics():
    """Prometheus scrape endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/internal/tasks/mission_handler", tags=["Internal"])
async def cloud_tasks_mission_handler(request: dict):
    """GCP Cloud Tasks webhook for background mission execution."""
    from backend.tasks import execute_mission_from_cloud_task
    mission_id = request.get("mission_id")
    payload    = request.get("payload", {})
    if not mission_id or not payload:
        raise HTTPException(status_code=400, detail="Invalid mission payload")
    logger.info("📥 [InternalTask] Cloud Task trigger: %s", mission_id)
    success = await execute_mission_from_cloud_task(mission_id, payload)
    if not success:
        raise HTTPException(status_code=500, detail="Execution failed")
    return {"status": "success", "mission_id": mission_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT") == "development",
        workers=int(os.getenv("WORKERS", "1")),
    )
