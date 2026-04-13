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
from backend.auth.middleware import SovereignShieldMiddleware
from backend.api.middleware.ssrf import SSRFMiddleware
from backend.api.middleware.rate_limiter import RateLimitMiddleware
from backend.api.middleware.prometheus import PrometheusMiddleware
from backend.utils.tracing import setup_tracing
from backend.auth import get_current_user
from backend.api.v1.voice import router as voice_router
from backend.api.v8.telemetry import router as telemetry_v8_router
from datetime import datetime, timezone
from fastapi.responses import JSONResponse
from backend.services.mcm import mcm_service
from backend.core.dcn.gossip import DCNGossip
from backend.db.redis import r_async as redis_async
from backend.services.ollama_health import ollama_monitor
from backend.services.health_monitor import health_monitor
from backend.core.goal_engine import goal_engine
from backend.services.voice.processor import AudioPulseProcessor

# Initialize logger
logger = logging.getLogger("levi")

# Global state
orchestrator: Orchestrator = None
memory_manager: MemoryManager = None
dcn_gossip: DCNGossip = None
audio_processor: AudioPulseProcessor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global orchestrator, memory_manager, dcn_gossip, audio_processor
    
    logger.info("🚀 LEVI-AI Sovereign OS v15.0.0-GA starting...")
    
    # Initialize core services
    orchestrator = Orchestrator()
    memory_manager = MemoryManager()
    
    await orchestrator.initialize()
    await memory_manager.initialize()
    
    # Link Orchestrator to GoalEngine
    goal_engine.orchestrator = orchestrator
    
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
            
            # 🚀 Step 5.3: Task Distribution (Remote Execution)
            elif pulse.payload_type == "remote_execution_request":
                # Check if this node is the intended target
                target_node = pulse.payload.get("target_node")
                local_node_id = dcn_protocol.node_id
                
                if target_node == local_node_id:
                    if orchestrator:
                        # Execute in background to avoid blocking the gossip listener
                        from backend.utils.runtime_tasks import create_tracked_task
                        create_tracked_task(
                            orchestrator.execute_remote_mission(pulse.mission_id, pulse.payload),
                            name=f"remote-exec-{pulse.mission_id}"
                        )
                    else:
                        logger.warning(f"⚠️ [DCN] Remote task rejected: Orchestrator uninitialized on {local_node_id}")
                else:
                    logger.debug(f"[DCN] Remote task for {target_node} ignored by {local_node_id}")
        dcn_gossip = dcn_protocol.gossip
        await dcn_protocol.start_listener(dcn_handler)
    
    # 5. Starting DCN Global Bridge
    from backend.utils.global_gossip import global_swarm_bridge
    from backend.memory.vector_store import SovereignVectorStore
    await global_swarm_bridge.initialize()
    await global_swarm_bridge.start()
    
    # 6. Background Memory Sync (v14.2 Hardened)
    from backend.utils.runtime_tasks import create_tracked_task
    create_tracked_task(SovereignVectorStore.reindex_global_memory(), name="faiss-global-reindex")
    
    # 7. Start Health, Model & Goal Monitors (v15.0 GA)
    await ollama_monitor.start()
    await health_monitor.start()
    await goal_engine.start()
    
    # 8. Start Memory Maintenance Loops (v15.0 Full Fulfillment)
    from backend.memory.background_reindexer import BackgroundReindexer
    reindexer = BackgroundReindexer(interval_seconds=3600)
    create_tracked_task(reindexer.start(), name="background-reindexer")
    
    # MCM Reconciliation Pulse
    async def mcm_reconciliation_pulse():
        while True:
            await mcm_service.run_reconciliation()
            await asyncio.sleep(60) # 1 minute pulse
    create_tracked_task(mcm_reconciliation_pulse(), name="mcm-reconciliation")
    
    # 9. Start Audio Pulse Recon (Phase 5)
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
    
    # 2. Stop Monitoring & Goal Services
    await health_monitor.stop()
    await ollama_monitor.stop()
    await goal_engine.stop()
    
    if audio_processor:
        audio_processor.stop()
        
    await memory_manager.shutdown()
    logger.info("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="LEVI-AI Sovereign OS",
    version="15.0.0-GA",
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
            "ollama": "unknown",
            "global_sync": "active" if HAS_PUBSUB else "degraded ⚠️"
        },
        "swarm_info": {
            "node_id": dcn_gossip.node_id if dcn_gossip else "standalone",
            "coordinator": "active" if (dcn_gossip and dcn_gossip.is_coordinator) else "follower",
            "term": dcn_gossip.current_term if dcn_gossip else 0
        },
        "graduation_score": await orchestrator.get_graduation_score() if orchestrator else 0.0
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
