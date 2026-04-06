"""
LEVI-AI: Local-First Distributed AI Stack v1.0.0-RC1.
Central Gateway & Service Orchestrator.
"""

import os
import logging
import time
import json
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.config.system import SOVEREIGN_VERSION, CLOUD_FALLBACK_ENABLED, CORS_ORIGINS

# Service Routers
from backend.api.v8.orchestrator import router as orchestrator_v1
from backend.api.v8.telemetry import router as telemetry_v1
from backend.api.v8.memory import router as memory_v1
from backend.api.v8.search import router as search_v1
from backend.api.v1.payments import router as payments_v1
from backend.api.v8.auth import router as auth_v1
from backend.api.billing import router as billing_v1
from backend.api.analytics import router as analytics_v1
from backend.api.agents import router as agents_v1
from backend.api.marketplace import router as marketplace_v1
from backend.api.compliance import router as compliance_v1
from backend.api.scheduling import router as scheduling_v1

# Core Logic
from backend.db.postgres_db import verify_resonance
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LEVI-AI Distributed Stack",
    version=SOVEREIGN_VERSION,
    description="Local-First Agentic Infrastructure (v1.0.0-RC1 Graduation)"
)

# 1. Security Hardening (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# 4. Startup Health & Integrity Audit
@app.on_event("startup")
async def graduation_audit():
    logger.info(f"🛡️ Validating LEVI-AI Stack Graduation ({SOVEREIGN_VERSION})...")
    logger.info(f"☁️ Cloud Fallback: {'ENABLED' if CLOUD_FALLBACK_ENABLED else 'DISABLED (Local-Only Mode)'}")
    
    try:
        if await verify_resonance():
            logger.info("✅ Database resonance confirmed. Local persistence active.")
        else:
            logger.warning("⚠️ Database sync drift detected.")
    except Exception as e:
        logger.error(f"❌ Startup Audit failed: {e}")

@app.get("/")
@app.get("/health")
async def health_status():
    """Official Pulse of the Distributed AI Stack."""
    return {
        "status": "online",
        "version": SOVEREIGN_VERSION,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "cloud_fallback": CLOUD_FALLBACK_ENABLED,
        "resonance": "GRADUATED"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
