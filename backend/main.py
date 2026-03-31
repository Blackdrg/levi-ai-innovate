# pyright: reportMissingImports=false
import os
import time
import uuid
import logging
import hmac
import json
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, status, BackgroundTasks  # type: ignore
from fastapi.responses import JSONResponse, StreamingResponse  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.middleware.gzip import GZipMiddleware  # type: ignore
from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore
from pydantic import BaseModel, Field  # type: ignore
from dotenv import load_dotenv

import sentry_sdk  # type: ignore
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
from slowapi import Limiter  # type: ignore
from slowapi.util import get_remote_address  # type: ignore
from slowapi.errors import RateLimitExceeded  # type: ignore
from slowapi import _rate_limit_exceeded_handler  # type: ignore

from backend.utils.logger import setup_logging, get_logger
from backend.utils.logging_context import log_request_id, log_user_id, log_session_id
from backend.models import _INJECTION_PATTERNS
from backend.firestore_db import db as firestore_db
from backend.redis_client import HAS_REDIS, REDIS_URL, r as redis_client
from backend.auth import get_current_user, get_current_user_optional, verify_admin
from google.cloud import firestore  # type: ignore

# ── Phase 4 Hardened Environment & Logging ────────────────
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

setup_logging()
logger = get_logger("main")

# Sentry Initialization
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    logger.info("Sentry initialized.")

# Instance Fingerprinting
INSTANCE_ID = str(uuid.uuid4())[:8]
logger.info(f"Initialized with Instance ID: {INSTANCE_ID}")

# Cloud Logging Integration (Production)
if os.getenv("ENVIRONMENT") == "production":
    try:
        import google.cloud.logging
        client = google.cloud.logging.Client()
        client.setup_logging()
        logger.info("Cloud Logging setup complete.")
    except Exception as e:
        logger.warning(f"Failed to setup Cloud Logging: {e}")

# Environment Validation
REQUIRED_ENV_VARS = [
    "SECRET_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET", "ADMIN_KEY", "FIREBASE_PROJECT_ID",
    "FIREBASE_SERVICE_ACCOUNT_JSON"
]

def validate_env():
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if not missing:
        logger.info("Environment validation successful.")
        return True

    if missing and os.getenv("ENVIRONMENT") == "production":
        logger.warning(f"Required vars missing: {', '.join(missing)}")
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("FIREBASE_PROJECT_ID") or "levi-ai-c23c6"
            for var in missing:
                try:
                    name = f"projects/{project_id}/secrets/{var}/versions/latest"
                    res = client.access_secret_version(name=name)
                    os.environ[var] = res.payload.data.decode("UTF-8")
                    logger.info(f"Fetched {var} from Secret Manager.")
                except Exception: pass
        except Exception: pass

    still_missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if still_missing and os.getenv("ENVIRONMENT") == "production":
        logger.critical(f"CRITICAL: Missing vars: {', '.join(still_missing)}")
        return False
    return True

validate_env()


# ── Lifespan & Heartbeats ───────────────────────────
async def instance_heartbeat(instance_id: str):
    """Register this instance in Redis every 30s for cluster visibility."""
    while True:
        try:
            if HAS_REDIS:
                redis_client.hset("active_instances", instance_id, int(time.time()))
                all_instances = redis_client.hgetall("active_instances")
                for inst, ts in all_instances.items():
                    if int(time.time()) - int(ts) > 60:
                        redis_client.hdel("active_instances", inst)
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
        await asyncio.sleep(30)

async def finetune_poller():
    """Periodically check Together AI fine-tuning status."""
    from backend.services.orchestrator.fine_tune_tasks import poll_finetune_status
    while True:
        try:
            await poll_finetune_status()
        except Exception as e:
            logger.warning(f"Finetune poll failed: {e}")
        await asyncio.sleep(300) # Poll every 5 mins

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting LEVI Heart [{INSTANCE_ID}]...")
    heartbeat_task = None
    finetune_task = None
    if os.getenv("DISABLE_BACKGROUND_TASKS") != "true":
        heartbeat_task = asyncio.create_task(instance_heartbeat(INSTANCE_ID))
        finetune_task = asyncio.create_task(finetune_poller())
    
    try:
        firestore_db.collection("health_check").document("status").get(timeout=5.0)
        logger.info("Firestore connection verified.")
        
        # Broadcast Activity Initialization
        from backend.broadcast_utils import register_broadcaster
        register_broadcaster(broadcast_activity, INSTANCE_ID)
        
        # Cleanup zombie tasks on startup
        zombie_jobs = firestore_db.collection("jobs").where("status", "==", "processing").get(timeout=5.0)
        for doc in zombie_jobs:
            doc.reference.update({
                "status": "failed", 
                "error": "Server restarted during processing",
                "completed_at": datetime.utcnow()
            })
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        if os.getenv("ENVIRONMENT") == "production":
             logger.error("CRITICAL: Initial database connection failed. Service may be degraded.")
    yield
    if heartbeat_task:
        heartbeat_task.cancel()
    if finetune_task:
        finetune_task.cancel()
    if HAS_REDIS:
        redis_client.hdel("active_instances", INSTANCE_ID)
    logger.info(f"Stopping LEVI Heart [{INSTANCE_ID}]...")

app = FastAPI(
    title="LEVI API",
    version="6.0.0",
    lifespan=lifespan,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs"
)


# ── Middleware Stack ──────────────────────────────────────
# CORS Configuration
origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:8080", "http://127.0.0.1:8080",
    "https://levi-ai-c23c6.web.app",
    "https://levi-ai-c23c6.firebaseapp.com",
    "https://levi-ai.vercel.app"
]
env_origins = os.getenv("CORS_ORIGINS", "").split(",")
for o in env_origins:
    if o.strip() and o.strip() not in origins:
        origins.append(o.strip())

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 8: Unified Observability & Tracing Middleware
class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        
        # LEVI v6: Standardized Context Extraction
        session_id = request.headers.get("X-Session-ID") or request.cookies.get("session_id", "none")
        user_tier = request.headers.get("X-User-Tier", "free")
        user_id = request.headers.get("X-User-ID", "anonymous")

        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.session_id = session_id
        request.state.user_tier = user_tier
        request.state.user_id = user_id
        
        t_rid = log_request_id.set(request_id)
        t_sid = log_session_id.set(session_id)
        log_user_id.set(user_id)
        
        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000
            
            # Log with full context for pattern analysis (Shared Learning Phase)
            logger.info(
                f"[{request.method}] {request.url.path} - {response.status_code} ({int(duration)}ms)",
                extra={
                    "request_id": request_id, 
                    "trace_id": trace_id,
                    "user_tier": user_tier,
                    "session_id": session_id
                }
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id
            return response
        finally:
            log_request_id.reset(t_rid)
            log_session_id.reset(t_sid)

app.add_middleware(ObservabilityMiddleware)

@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    """Firebase Hosting compatibility prefix stripping."""
    path = request.scope["path"]
    if path.startswith("/api/v1"):
        request.scope.update({"path": path[7:] or "/"})
    elif path.startswith("/api"):
        request.scope.update({"path": path[4:] or "/"})
    return await call_next(request)


# ── Modular Routers (v6 Architecture) ─────────────────────────
from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.studio import router as studio_router
from backend.api.gallery import router as gallery_router
from backend.api.payments import router as payments_router
from backend.api.learning import router as learning_router
from backend.api.orchestrator import router as orchestrator_router
from backend.api.ai_studio import router as ai_studio_router
from backend.api.privacy import router as privacy_router
from backend.api.analytics import router as analytics_router
from backend.api.monitor_routes import router as monitor_router
from backend.api.search import router as search_router
from backend.api.documents import router as documents_router

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(search_router, prefix="/search", tags=["Search"])
app.include_router(studio_router, prefix="/studio", tags=["Studio"])
app.include_router(ai_studio_router, prefix="/studio/advanced", tags=["AI Studio"])
app.include_router(gallery_router, prefix="/gallery", tags=["Gallery"])
app.include_router(payments_router, prefix="/user/payments", tags=["Payments"])
app.include_router(privacy_router, prefix="/user/privacy", tags=["Privacy"])
app.include_router(learning_router, prefix="/learning", tags=["Learning"])
app.include_router(orchestrator_router, prefix="/system/orchestrator", tags=["Orchestrator"])
app.include_router(analytics_router, prefix="/system/analytics", tags=["Analytics"])
app.include_router(monitor_router, prefix="/system/monitor", tags=["Monitoring"])
app.include_router(documents_router, prefix="/upload", tags=["Documents"])

# ── Contract Aliases (Phase 6 Production Alignment) ──
app.include_router(privacy_router, prefix="/memory", tags=["Contract"])
app.include_router(monitor_router, prefix="/status", tags=["Contract"])
app.include_router(learning_router, prefix="/features", tags=["Contract"])


# ── Global Error Handling ────────────────────────
from backend.utils.error_handler import levi_exception_handler, global_exception_handler
from backend.utils.exceptions import LEVIException

app.add_exception_handler(LEVIException, levi_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Restored Legacy Endpoints ────────────────────────

@app.post("/razorpay_webhook")
async def razorpay_webhook(request: Request):
    """Critical for async payment capture and tier upgrades."""
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    if not webhook_secret or not signature:
        return {"status": "ignored"}

    expected = hmac.new(webhook_secret.encode(), payload, digestmod=hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(payload)
    if data.get("event") == "payment.captured":
        payment = data["payload"]["payment"]["entity"]
        user_id = payment.get("notes", {}).get("user_id")
        plan = payment.get("notes", {}).get("plan", "pro")
        if user_id:
            from backend.payments import upgrade_user_tier
            upgrade_user_tier(user_id, plan)
            logger.info(f"Payment captured via webhook for user {user_id}")

    return {"status": "success"}

@app.post("/track_share")
async def track_share(current_user: dict = Depends(get_current_user)):
    """Track viral shares and reward bonus credits."""
    uid = current_user.get("uid")
    user_ref = firestore_db.collection("users").document(uid)
    user_ref.update({"share_count": firestore.Increment(1)})
    
    new_shares = current_user.get("share_count", 0) + 1
    if new_shares % 5 == 0:
        user_ref.update({"credits": firestore.Increment(50)})
        return {"status": "rewarded", "bonus": 50}
    return {"status": "success"}

@app.get("/push/vapid_public_key")
async def get_vapid_public_key():
    return {"public_key": os.getenv("VAPID_PUBLIC_KEY")}

@app.post("/push/subscribe")
async def subscribe_push(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    uid = current_user.get("uid")
    firestore_db.collection("push_subscriptions").document(uid).set({
        "subscription": data,
        "updated_at": datetime.utcnow()
    })
    return {"status": "subscribed"}

@app.get("/daily_quote")
async def get_daily_quote(mood: str = "philosophical"):
    """Fetch the daily OS-source quote fallback."""
    from backend.generation import fetch_open_source_quote
    quote = fetch_open_source_quote(mood)
    return quote or {"quote": "Know thyself.", "author": "Socrates"}


# ── Phase 44: Real-Time Omnipresence (SSE) ──────────────────

@app.get("/stream")
async def activity_stream(request: Request):
    """SSE endpoint for real-time global activity and Meta-Brain strategy."""
    if not HAS_REDIS:
        raise HTTPException(status_code=503, detail="Stream requires Redis")

    async def event_generator():
        from backend.redis_client import get_async_redis
        async_r = await get_async_redis()
        pubsub = async_r.pubsub()
        await pubsub.subscribe("levi_activity")
        
        yield "retry: 2000\n"
        yield "data: {\"event\":\"connected\",\"msg\":\"Cosmic link established\"}\n\n"

        try:
            async for message in pubsub.listen():
                if request.is_disconnected(): break
                if message["type"] == "message":
                    yield f"data: {message['data'].decode('utf-8')}\n\n"
        finally:
            await pubsub.unsubscribe("levi_activity")
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

def broadcast_activity(event_type: str, data: Dict[str, Any]):
    """Push an event to the Global Activity channel."""
    if not HAS_REDIS: return
    try:
        payload = json.dumps({
            "event": event_type, "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "instance": INSTANCE_ID
        })
        redis_client.publish("levi_activity", payload)
    except Exception as e:
        logger.warning(f"Broadcast failed: {e}")


# ── Global Entry Points ────────────────────────────

@app.get("/")
async def root(response: Response):
    response.headers["X-Evolution-Instance"] = INSTANCE_ID
    return {
        "status": "active",
        "heart": "LEVI v6 Sovereign",
        "instance": INSTANCE_ID,
        "evolution": "v6.0.0-PRO",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/evolution")
async def evolution_health(response: Response, current_user: dict = Depends(verify_admin)):
    """
    LEVI v6: Monitor the autonomous growth and collective wisdom of the system.
    """
    from backend.learning import get_learning_stats
    stats = get_learning_stats()
    response.headers["X-Evolution-Instance"] = INSTANCE_ID
    
    return {
        "heart": "Evolutionary Core v6",
        "metrics": {
            "total_samples": stats.get("total_training_samples", 0),
            "hq_samples": stats.get("high_quality_samples", 0),
            "avg_rating": stats.get("avg_response_rating", 0.0),
            "learned_quotes": stats.get("learned_quotes", 0),
            "best_variant": stats.get("best_prompt_variant", 0),
            "best_score": stats.get("best_prompt_score", 0.0)
        },
        "status": "evolving" if stats.get("knowledge_base_health") == "growing" else "stable",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    """
    Production-grade Health Check v6.8.
    Performs 'Sovereign Engine Probe' across all critical infrastructure.
    """
    import asyncio
    from backend.utils.network import safe_request
    
    db_ok = False
    try:
        firestore_db.collection("health_check").document("status").get(timeout=3.0)
        db_ok = True
    except: pass
    
    redis_ok = False
    try:
        if HAS_REDIS: 
            redis_client.ping()
            redis_ok = True
    except: pass
    
    # ── Sovereign Engine Probe ──
    engines = {
        "logic_db": "connected" if db_ok else "error",
        "memory_cache": "connected" if redis_ok else "error",
        "together_ai": "checking",
        "groq_primary": "checking"
    }
    
    # Quick connectivity checks (non-blocking)
    if os.getenv("TOGETHER_API_KEY"):
        engines["together_ai"] = "online" # Basic key presence for now
    if os.getenv("GROQ_API_KEY"):
        engines["groq_primary"] = "online"

    return {
        "status": "ready" if (db_ok and redis_ok) else "degraded",
        "instance_id": INSTANCE_ID,
        "engines": engines,
        "sovereign_v6": "hardened",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
