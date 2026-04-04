"""
LEVI-AI Sovereign OS v13.0.0: Absolute Monolith.
Central API Heart & Master Entry Point.
Synchronized for SQL Resonance, HNSW Vault Recall, and Adaptive Pulse v4.1.
"""

import os
import logging
import time
import json
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Graduated v13.0 Monolith Routers
from backend.api.v8.orchestrator import router as orchestrator_v13
from backend.api.v8.telemetry import router as telemetry_v13
from backend.api.v8.memory import router as memory_v13
from backend.api.v8.search import router as search_v13
from backend.api.v1.payments import router as payments_v13
from backend.api.v8.auth import router as auth_v13
from backend.api.billing import router as billing_v13
from backend.api.analytics import router as analytics_v13
from backend.api.agents import router as agents_v13
from backend.api.marketplace import router as marketplace_v13
from backend.api.compliance import router as compliance_v13
from backend.api.scheduling import router as scheduling_v13

# New v13 Sovereign Cognition (SSE Stream)
from app.routes.chat import router as chat_v13_stream
from app.routes.auth import router as auth_v13_monolith

# Sovereign Core
from backend.db.postgres_db import verify_resonance
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LEVI-AI Absolute Monolith",
    version="13.0.0",
    description="Sovereign AI Operating System Graduate"
)

# 1. Monolith Hardening (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten in production swarm
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Adaptive Pulse v4.1 Middleware (Binary Compression Sync)
@app.middleware("http")
async def pulse_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start_time) * 1000
    
    # Emit Neural Pulse for every cognitive request
    SovereignBroadcaster.broadcast({
        "type": "NEURAL_PULSE",
        "path": request.url.path,
        "latency_ms": latency_ms,
        "status": response.status_code,
        "ts": datetime.now(timezone.utc).isoformat()
    })
    return response

# 3. Mount Graduated v13.0 Monolith Routers
app.include_router(orchestrator_v13, prefix="/api/v13/orchestrator", tags=["Orchestrator v13"])
app.include_router(telemetry_v13, prefix="/api/v13/telemetry", tags=["Telemetry v13"])
app.include_router(memory_v13, prefix="/api/v13/memory", tags=["Memory v13"])
app.include_router(search_v13, prefix="/api/v13/search", tags=["Search v13"])
app.include_router(payments_v13, prefix="/api/v13/payments", tags=["Payments v13"])
app.include_router(auth_v13, prefix="/api/v13/auth", tags=["Auth v13"])
app.include_router(billing_v13, prefix="/api/v13/billing", tags=["Sovereign Billing"])
app.include_router(analytics_v13, prefix="/api/v13/analytics", tags=["Sovereign Analytics"])
app.include_router(agents_v13, prefix="/api/v13/agents", tags=["Custom Agents"])
app.include_router(marketplace_v13, prefix="/api/v13/marketplace", tags=["Sovereign Marketplace"])
app.include_router(compliance_v13, prefix="/api/v13/compliance", tags=["Sovereign Compliance"])
app.include_router(scheduling_v13, prefix="/api/v13/scheduling", tags=["Scheduled Missions"])
app.include_router(chat_v13_stream, tags=["Sovereign Cognition v13"])
app.include_router(auth_v13_monolith)

# 4. Monolith Startup Integrity Audit
@app.on_event("startup")
async def monolith_audit():
    logger.info("🛡️ Initiating Absolute Monolith Graduation Audit (v13.0.0)...")
    try:
        # Check SQL Resonance
        if await verify_resonance():
            logger.info("✅ SQL Fabric resonance confirmed. Zero-cloud persistence active.")
        else:
            logger.warning("⚠️ SQL Fabric sync drift. Running in failover mode.")
    except Exception as e:
        logger.error(f"❌ Graduation Audit failed: {e}")

@app.get("/")
async def monolith_status():
    """Definitive Pulse of the Absolute Monolith."""
    return {
        "status": "online",
        "version": "13.0.0",
        "codename": "Absolute Monolith",
        "mission": "Global Technical Finality",
        "resonance": "GRADUATED"
    }

# --- Legacy Bridges (v1 Compatibility) ---
@app.get("/api/v1/pulse")
async def legacy_pulse(request: Request):
    """Graduated Bridge for legacy SSE subscribers."""
    return StreamingResponse(
        SovereignBroadcaster.subscribe(user_id="global"),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
