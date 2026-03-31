# pyright: reportMissingImports=false
import os
import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from backend.utils.logging_context import log_request_id, log_user_id

from fastapi import FastAPI, Request, HTTPException, Depends, status, BackgroundTasks  # type: ignore
from fastapi.responses import JSONResponse, StreamingResponse  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.middleware.gzip import GZipMiddleware # type: ignore
from starlette.middleware.base import BaseHTTPMiddleware # type: ignore
from pydantic import BaseModel, Field, field_validator # type: ignore
import hmac
import json
import numpy as np
from backend.models import _INJECTION_PATTERNS # type: ignore
from dotenv import load_dotenv

import sentry_sdk # type: ignore
from pythonjsonlogger.json import JsonFormatter # type: ignore
from slowapi import Limiter # type: ignore
from slowapi.util import get_remote_address # type: ignore
from slowapi.errors import RateLimitExceeded # type: ignore
from slowapi import _rate_limit_exceeded_handler # type: ignore

from slowapi.errors import RateLimitExceeded # type: ignore
from slowapi import _rate_limit_exceeded_handler # type: ignore

# ── Environment & Logging ───────────────────────────
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

class CustomJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        
        # Add context-aware fields
        log_record['request_id'] = log_request_id.get()
        log_record['user_id'] = log_user_id.get()
        log_record['instance_id'] = os.getenv("INSTANCE_ID", "unknown")

logger = logging.getLogger("gateway")
logHandler = logging.StreamHandler()
formatter = CustomJsonFormatter(fmt='%(timestamp)s %(level)s %(name)s %(message)s') # type: ignore
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
logger.propagate = False

# Sentry Initialization
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    logger.info("Sentry initialized in Gateway.")

# Instance Fingerprinting
INSTANCE_ID = str(uuid.uuid4())[:8]
logger.info(f"Initialized with Instance ID: {INSTANCE_ID}")

# Phase 46: Cloud Logging Integration
if os.getenv("ENVIRONMENT") == "production":
    try:
        import google.cloud.logging
        client = google.cloud.logging.Client()
        client.setup_logging()
        logger.info("Cloud Logging setup complete.")
    except Exception as e:
        print(f"Failed to setup Cloud Logging: {e}")

# Environment Validation
REQUIRED_ENV_VARS = [
    "SECRET_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET", "ADMIN_KEY", "FIREBASE_PROJECT_ID",
    "FIREBASE_SERVICE_ACCOUNT_JSON"
]


def validate_env():
    """Phase 40: Enhanced Env Validation with Secret Manager Fallback."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    
    if not missing:
        logger.info("Environment validation successful. All required variables present.")
        return True

    # ── Secret Manager Fallback (Production) ──────────────────────
    if missing and os.getenv("ENVIRONMENT") == "production":
        logger.warning(f"Required variables missing from environment: {', '.join(missing)}")
        logger.info("Attempting Secret Manager fallback...")
        try:
            from google.cloud import secretmanager # type: ignore
            client = secretmanager.SecretManagerServiceClient()
            # Fallback to firestore project ID if not set
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIREBASE_PROJECT_ID") or "levi-ai-c23c6"
            
            for var in missing:
                name = f"projects/{project_id}/secrets/{var}/versions/latest"
                try:
                    response = client.access_secret_version(name=name)
                    val = response.payload.data.decode("UTF-8")
                    os.environ[var] = val
                    logger.info(f"Successfully retrieved {var} from Secret Manager.")
                except Exception as e:
                    logger.error(f"Failed to fetch {var} from Secret Manager: {e}")
        except ImportError:
            logger.error("google-cloud-secret-manager dependency missing. Check requirements.prod.txt.")
        except Exception as e:
            logger.error(f"Secret Manager client failure: {e}")

    # Final check
    still_missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if still_missing and os.getenv("ENVIRONMENT") == "production":
        logger.critical(f"UNRECOVERABLE: Missing critical environment variables: {', '.join(still_missing)}")
        logger.critical("Server will start but API requests requiring these secrets will fail.")
        # We NO LONGER exit(1) here to allow the container to start and report health logs.
        # This helps debug why the deployment is failing.
        return False
    
    # Standardize Service Account Parsing for Cloud Run
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        try:
            if sa_json.startswith("{") and sa_json.endswith("}"):
                json.loads(sa_json)
                logger.info("Firebase Service Account JSON string validated.")
            elif os.path.exists(sa_json):
                 logger.info(f"Firebase Service Account file found: {sa_json}")
        except Exception as e:
            logger.error(f"Invalid FIREBASE_SERVICE_ACCOUNT_JSON format: {e}")
    
    if not os.getenv("ALERT_WEBHOOK_URL"):
        logger.info("Optional ALERT_WEBHOOK_URL not set. Proactive monitoring alerts disabled.")
    else:
        logger.info("Proactive monitoring alerts ENABLED.")

    return True

try:
    ENV_LOADED = validate_env()
except Exception as e:
    logger.error(f"Critical error during environment validation: {e}")
    ENV_LOADED = False

# Note: validate_env() is called above after definition

# ── Lifespan & Heartbeats ───────────────────────────
from backend.firestore_db import db as firestore_db # type: ignore
from backend.redis_client import HAS_REDIS, REDIS_URL, r as redis_client # type: ignore
import asyncio

async def instance_heartbeat(instance_id: str):
    """Phase 41: Register this instance in Redis every 30s for cluster visibility."""
    while True:
        try:
            if HAS_REDIS:
                # Store heartbeat in a Hash: Key=active_instances, Field=instance_id, Val=timestamp
                redis_client.hset("active_instances", instance_id, int(time.time()))
                # Cleanup old heartbeats (> 60s)
                all_instances = redis_client.hgetall("active_instances")
                for inst, ts in all_instances.items():
                    if int(time.time()) - int(ts) > 60:
                        redis_client.hdel("active_instances", inst)
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting LEVI Gateway [{INSTANCE_ID}]...")
    
    # Start Heartbeat Task
    heartbeat_task = None
    if os.getenv("DISABLE_BACKGROUND_TASKS") != "true":
        heartbeat_task = asyncio.create_task(instance_heartbeat(INSTANCE_ID))
    
    try:
        firestore_db.collection("health_check").document("status").get(timeout=5.0)
        logger.info("Firestore connection verified.")
        
        # Register broadcaster so service routers can use it safely
        from backend.broadcast_utils import register_broadcaster
        register_broadcaster(broadcast_activity, INSTANCE_ID)
        
        # Cleanup zombie tasks (with timeout to prevent startup hang)
        try:
            zombie_jobs = firestore_db.collection("jobs") \
                .where("status", "==", "processing").get(timeout=5.0)
            for doc in zombie_jobs:
                doc.reference.update({
                    "status": "failed", 
                    "error": "Server restarted during processing",
                    "completed_at": datetime.utcnow()
                })
        except Exception as ze:
            logger.warning(f"Zombie job cleanup skipped or failed: {ze}")
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        # In production, we don't crash the whole process just for a transient network error,
        # but we log it as critical.
        if os.getenv("ENVIRONMENT") == "production":
            logger.error("CRITICAL: Initial database connection failed. Service may be degraded.")
    
    logger.info(f"LEVI Gateway v4.0 Pulse [{INSTANCE_ID}] Initialized Successfully.")
    yield
    # Stop Heartbeat
    if heartbeat_task:
        heartbeat_task.cancel()
    if HAS_REDIS:
        redis_client.hdel("active_instances", INSTANCE_ID)
    logger.info(f"Stopping LEVI Gateway [{INSTANCE_ID}]...")

app = FastAPI(
    title="LEVI API Gateway",
    version="4.5.1",
    lifespan=lifespan,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs"
)



# ── Middleware ──────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL if HAS_REDIS else "memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def add_request_tracking(request: Request, call_next):
    """Phase 40: Advanced Global Observability Middleware."""
    request_id = str(uuid.uuid4())
    # Distributed Trace-ID Injection
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    
    request.state.request_id = request_id
    request.state.trace_id = trace_id
    
    # Set context variables
    log_request_id.set(request_id)
    # user_id will be set later in auth middleware or routers if available
    # For now, initialize with guest or trace_id
    log_user_id.set(request.headers.get("X-User-ID", "anonymous"))
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate performance metrics
    duration = (time.time() - start_time) * 1000
    p_size = response.headers.get("Content-Length", "0")
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_id
    
    # Phase 42: Cache Isolation (Vary)
    response.headers["Vary"] = "Accept-Encoding, Authorization, X-Trace-ID"
    
    # Phase 45: Real-Time Metric Accumulation (Redis Aggregation)
    if HAS_REDIS:
        try:
            # 1. Throughput increment
            redis_client.incr("metrics:total_requests")
            
            # 2. Latency aggregation (p95 history)
            redis_client.lpush("metrics:latency_ms", int(duration))
            redis_client.ltrim("metrics:latency_ms", 0, 99) # Keep last 100 durations
            
            # 3. Error monitoring
            if response.status_code >= 500:
                redis_client.incr("metrics:error_count")
        except Exception as e:
            logger.warning(f"Metric push failed: {e}")

    logger.info("gateway_request_completed", extra={
        "request_id": request_id, 
        "trace_id": trace_id,
        "method": request.method,
        "path": request.url.path, 
        "status_code": response.status_code,
        "duration_ms": int(duration),
        "payload_size_kb": round(int(p_size) / 1024, 2) if p_size.isdigit() else 0,
        "cache_hit": response.headers.get("X-Cache", "MISS")
    })
    
    # ── Phase 22: Ultimate Security Hardening ──────────────────
    # Content Security Policy (CSP)
    csp_parts = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.gstatic.com https://checkout.razorpay.com https://cdn.jsdelivr.net https://www.googletagmanager.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
        "img-src 'self' data: blob: https://images.unsplash.com https://*.firebasestorage.app https://*.s3.amazonaws.com https://www.google-analytics.com",
        "connect-src 'self' https://*.firebaseio.com https://*.googleapis.com https://api.razorpay.com https://www.google-analytics.com https://stats.g.doubleclick.net",
        "font-src 'self' https://fonts.gstatic.com",
        "frame-src 'self' https://checkout.razorpay.com",
        "object-src 'none'",
        "upgrade-insecure-requests"
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_parts)
    
    # HSTS (force HTTPS)
    if os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Standard Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-DNS-Prefetch-Control"] = "off"
    response.headers["Expect-CT"] = "max-age=86400, enforce"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    
    return response

@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    """Strip /api/v1 and /api prefixes for Firebase Hosting compatibility."""
    path = request.scope["path"]
    if path.startswith("/api/v1"):
        new_path = path[len("/api/v1"):] or "/"
        request.scope.update({"path": new_path})
    elif path.startswith("/api"):
        new_path = path[len("/api"):] or "/"
        request.scope.update({"path": new_path})
    
    return await call_next(request)

# CORS
origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "https://levi-ai-c23c6.web.app",
    "https://levi-ai.cr",
    "https://www.levi-ai.cr",
    "https://levi-ai.vercel.app"
]
env_origins = os.getenv("CORS_ORIGINS", "").split(",")
for o in env_origins:
    if o.strip() and o.strip() not in origins:
        origins.append(o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ─────────────────────────────────────────
from backend.services.auth.router import router as auth_router # type: ignore
from backend.services.chat.router import router as chat_router # type: ignore
from backend.services.orchestrator.router import router as orchestrator_router # type: ignore
from backend.services.orchestrator.privacy_router import router as privacy_router # type: ignore
from backend.services.studio.router import router as studio_router # type: ignore
from backend.services.gallery.router import router as gallery_router # type: ignore
from backend.services.analytics.router import router as analytics_router # type: ignore
from backend.payments import router as payments_router # type: ignore
from backend.services.studio.ai_router import router as ai_router # type: ignore
from backend.services.learning.router import router as learning_router # type: ignore

# Phase 2: Standardized Route Architecture
# Note: Middleware strips /api/v1 and /api, so we register canonical paths.
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(studio_router, prefix="/studio", tags=["Studio"])
app.include_router(ai_router, prefix="/studio/advanced", tags=["AI Studio"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(payments_router, prefix="/user/payments", tags=["Payments"])
app.include_router(privacy_router, prefix="/user/privacy", tags=["Privacy"])
app.include_router(analytics_router, prefix="/system/analytics", tags=["Analytics"])
app.include_router(orchestrator_router, prefix="/system/orchestrator", tags=["Orchestrator"])
app.include_router(gallery_router, prefix="/gallery", tags=["Gallery"])
app.include_router(learning_router, prefix="", tags=["Learning"])  # /feedback, /learning/*, /model/*

# ── Global Error Handling ───────────────────────────
from backend.utils.exceptions import LEVIException

@app.exception_handler(LEVIException)
async def levi_exception_handler(request: Request, exc: LEVIException):
    rid = getattr(request.state, "request_id", "unknown")
    uid = getattr(request.state, "user_id", log_user_id.get("anonymous"))

    # Capture to Sentry with structured tags for triage dashboards
    if SENTRY_DSN:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error_code", exc.error_code)
            scope.set_tag("request_id", rid)
            scope.set_user({"id": uid})
            scope.set_extra("message", exc.message)
            scope.set_extra("status_code", exc.status_code)
            sentry_sdk.capture_exception(exc)

    logger.warning(
        "levi_exception",
        extra={
            "error_code": exc.error_code,
            "message": exc.message,
            "request_id": rid,
            "user_id": uid,
            "status_code": exc.status_code,
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "request_id": rid,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", "unknown")
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "request_id": rid})
    
    logger.error(f"Unhandled Error [RID: {rid}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred in the cosmic matrix.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "request_id": rid
        }
    )



# ── Phase 44: Real-Time Omnipresence (SSE) ──────────────────
@app.get("/stream")
async def activity_stream(request: Request):
    """
    SSE endpoint for real-time global activity.
    Listens to Redis Pub/Sub 'levi_activity' channel.
    """
    if not HAS_REDIS:
        raise HTTPException(status_code=503, detail="Stream requires Redis")

    async def event_generator():
        from backend.redis_client import get_async_redis # type: ignore
        async_r = await get_async_redis()
        pubsub = async_r.pubsub()
        await pubsub.subscribe("levi_activity")

        try:
            # Initial connection event
            yield "data: {\"event\":\"connected\",\"msg\":\"Cosmic link established\"}\n\n"
            
            async for message in pubsub.listen():
                if request.is_disconnected():
                    break
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    yield f"data: {data}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            await pubsub.unsubscribe("levi_activity")
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

def broadcast_activity(event_type: str, data: Dict[str, Any]):
    """Utility to push an event to the Global Activity channel."""
    if not HAS_REDIS: return
    try:
        payload = json.dumps({
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "instance": INSTANCE_ID
        })
        redis_client.publish("levi_activity", payload)
    except Exception as e:
        logger.warning(f"Broadcast failed: {e}")

# ── Legacy/Global Routes ────────────────────────────
@app.get("/")
async def root():
    return {
        "status": "ok", 
        "service": "LEVI Gateway", 
        "version": "3.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs": "/docs" if os.getenv("ENVIRONMENT") != "production" else None
    }

@app.get("/health")
async def health():
    """
    Robust health check for CI/CD and monitoring.
    Verifies Firestore connectivity.
    """
    status_info = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("GITHUB_SHA", "local")[:7],
        "database": "checking",
        "redis": "checking",
        "auth": "ok",
    }
    
    # 1. Check Firestore
    try:
        if firestore_db:
            firestore_db.collection("health_check").document("status").get(timeout=3.0)
            status_info["database"] = "ok"
        else:
            status_info["database"] = "not_initialized"
    except Exception as e:
        logger.error(f"Health Check: Firestore unreachable: {e}")
        status_info["database"] = "error"
        status_info["status"] = "error"
        
    # 2. Check Redis
    try:
        if HAS_REDIS:
            from backend.redis_client import r as redis_client
            redis_client.ping()
            status_info["redis"] = "ok"
        else:
            status_info["redis"] = "disabled"
    except Exception as e:
        logger.error(f"Health Check: Redis unreachable: {e}")
        status_info["redis"] = "error"
        # We don't fail the whole app for Redis if it's optional, 
        # but for hardening we report it.
        
    status_info["environment"] = os.getenv("ENVIRONMENT", "development")

    return status_info
