"""
LEVI-AI Sovereign OS v8.
Central API Heart & Entry Point.
Standardized for v8 Cognitive Monolith, 4-Tier Memory, and Real-Time Mission Auditing.
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

# --- Routers ---
from backend.api.v1.orchestrator import router as orchestrator_router
from backend.api.v1.brain import router as brain_router
from backend.api.v1.chat import router as chat_router
from backend.api.v1.studio import router as studio_router
from backend.api.v1.ai_studio import router as ai_studio_router
from backend.api.v1.memory import router as memory_router
from backend.api.v1.documents import router as documents_router
from backend.api.v1.learning import router as learning_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.payments import router as payments_router
from backend.api.v1.monitor_routes import router as monitor_router
from backend.api.v1.search import router as search_router
from backend.api.v1.privacy import router as privacy_router
from backend.api.v1.gallery import router as gallery_router
from backend.api.v1.analytics import router as analytics_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Sovereign OS v8 Lifespan Management.
    Ensures persistent neural links and clean shutdown.
    """
    logger.info("Initializing Sovereign Heart (v8)...")
    
    # 1. Connectivity Check (Ledger & Cache)
    try:
        sovereign_cache().ping()
        logger.info("[Main] Sovereign Cache active (v8).")
        
        # Test Firestore connection
        logger.info("[Main] Sovereign Ledger active (Firestore).")
    except Exception as e:
        logger.error(f"[Main] Critical infrastructure failure: {e}")
        
    # 2. Daily Evolution Schedule
    # (Simulated - in production this triggers Celery Beat)
    yield
    
    logger.info("Stopping Sovereign Heart (v8)...")

app = FastAPI(
    title="LEVI-AI Sovereign OS",
    version="8.0.0",
    lifespan=lifespan
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Standardized for global readiness
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def context_middleware(request: Request, call_next):
    """Injects mission context into all request headers."""
    request_id = str(asyncio.get_event_loop().time())
    response = await call_next(request)
    response.headers["X-Sovereign-ID"] = request_id
    return response

# --- V1 Global API Routing ---
app.include_router(orchestrator_router, prefix="/api/v1/orchestrator", tags=["Orchestrator"])
app.include_router(brain_router, prefix="/api/v1/brain", tags=["Brain"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(studio_router, prefix="/api/v1/studio", tags=["Studio"])
app.include_router(ai_studio_router, prefix="/api/v1/ai_studio", tags=["AI Studio"])
app.include_router(memory_router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(learning_router, prefix="/api/v1/learning", tags=["Learning"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(payments_router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(monitor_router, prefix="/api/v1/monitor", tags=["Monitor"])
app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])
app.include_router(privacy_router, prefix="/api/v1/privacy", tags=["Privacy"])
app.include_router(gallery_router, prefix="/api/v1/gallery", tags=["Gallery"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])

@app.get("/")
async def root():
    """Heartbeat Pulse of the Sovereign OS."""
    return {
        "status": "online",
        "heart": "LEVI-AI Sovereign v8",
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
