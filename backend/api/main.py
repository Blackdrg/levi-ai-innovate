"""
LEVI-AI Sovereign OS v9.8.1.
Central API Heart & Entry Point.
Standardized for v9 Cognitive Monolith, 4-Tier Memory, and Real-Time Mission Auditing.
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.auth.logic import get_current_user # Bridged for v8
from backend.db.redis import get_redis_client as sovereign_cache
from backend.db.firebase import db as sovereign_db
from backend.utils.broadcast import SovereignBroadcaster
from backend.config.system import CORS_ORIGINS, ENVIRONMENT

# --- Routers ---
# --- Routers (Sovereign v8 Consolidation) ---
from backend.api.v8.orchestrator import router as orchestrator_router
from backend.api.v8.chat import router as chat_router
from backend.api.v8.memory import router as memory_router
from backend.api.v8.documents import router as documents_router
from backend.api.v8.auth import router as auth_router
from backend.api.v8.payments import router as payments_router
from backend.api.v8.learning import router as learning_router
from backend.api.v8.search import router as search_router
from backend.api.v8.gallery_analytics import router as gallery_router
from backend.api.v8.privacy_studio import router as studio_router
from backend.api.v8.monitor import router as monitor_router

# --- V8 Sovereign Bridge ---
from backend.api.v8.mobile_auth import router as mobile_auth_router
from backend.api.v8.telemetry import router as telemetry_router
from backend.api.v8.shield import SovereignShieldMiddleware
from backend.api.v8.knowledge import router as knowledge_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Sovereign OS v8 Lifespan Management.
    Ensures persistent neural links and clean shutdown.
    """
    logger.info("Initializing Sovereign Heart (v9.8.1 Core)...")
    
    # 1. Connectivity Check (Ledger & Cache)
    try:
        sovereign_cache().ping()
        logger.info("[Main] Sovereign Cache (Redis) active.")
    except Exception as e:
        logger.error(f"[Main] Critical infrastructure failure: {e}")
        
    yield
    
    logger.info("Stopping Sovereign Heart (v9.8.1)...")

# --- Middleware ---
app = FastAPI(
    title="LEVI-AI Sovereign OS",
    version="9.8.1", # Consolidated V9 Monolith
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 7: Sovereign Shield Hardening
app.add_middleware(SovereignShieldMiddleware, rate_limit=150)

@app.middleware("http")
async def context_middleware(request: Request, call_next):
    """Injects mission context into all request headers (v8)."""
    request_id = str(asyncio.get_event_loop().time())
    response = await call_next(request)
    response.headers["X-Sovereign-ID"] = request_id
    response.headers["X-V8-Status"] = "evolutionary"
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Sovereign Shield: Suppresses stack traces in production."""
    logger.error(f"[SovereignShield] Unhandled exception: {exc}")
    detail = "Internal Sovereign error." if ENVIRONMENT == "production" else str(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": request.headers.get("X-Sovereign-ID")}
    )

# --- V8 Sovereign API Routing (Hard Cutover) ---
# All features consolidated under /api/v8/
app.include_router(orchestrator_router, prefix="/api/v8/orchestrator", tags=["Orchestrator V8"])
app.include_router(chat_router, prefix="/api/v8/chat", tags=["Chat V8"])
app.include_router(memory_router, prefix="/api/v8/memory", tags=["Memory V8"])
app.include_router(documents_router, prefix="/api/v8/documents", tags=["Documents V8"])
app.include_router(auth_router, prefix="/api/v8/auth", tags=["Auth V8"])
app.include_router(payments_router, prefix="/api/v8/payments", tags=["Payments V8"])
app.include_router(learning_router, prefix="/api/v8/learning", tags=["Learning V8"])
app.include_router(search_router, prefix="/api/v8/search", tags=["Search V8"])
app.include_router(gallery_router, prefix="/api/v8/gallery", tags=["Gallery V8"])
app.include_router(studio_router, prefix="/api/v8/studio", tags=["Studio V8"])
app.include_router(monitor_router, prefix="/api/v8/monitor", tags=["Monitor V8"])

# Sovereign Bridge Routing (Mobile & Telemetry)
app.include_router(mobile_auth_router, prefix="/api/v8/mobile")
app.include_router(telemetry_router, prefix="/api/v8/telemetry")
app.include_router(knowledge_router, prefix="/api/v8/knowledge")

@app.get("/")
async def root():
    """Heartbeat Pulse of the Sovereign OS."""
    return {
        "status": "online",
        "heart": "LEVI-AI Sovereign v9.8.1",
        "vision": "Global Readiness Complete",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/pulse")
async def global_pulse(request: Request):
    """SSE endpoint for global engine activity telemetry."""
    return StreamingResponse(
        SovereignBroadcaster.subscribe(user_id="global"),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
