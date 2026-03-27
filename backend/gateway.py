# pyright: reportMissingImports=false
import os
import time
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, status, BackgroundTasks  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from starlette.middleware.base import BaseHTTPMiddleware # type: ignore
from pydantic import BaseModel, Field, field_validator # type: ignore
import hmac
import numpy as np
from backend.models import _INJECTION_PATTERNS # type: ignore
from dotenv import load_dotenv

import sentry_sdk # type: ignore
from pythonjsonlogger.json import JsonFormatter # type: ignore
from slowapi import Limiter # type: ignore
from slowapi.util import get_remote_address # type: ignore
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

# Environment Validation
REQUIRED_ENV_VARS = [
    "SECRET_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET", "ADMIN_KEY", "FIREBASE_PROJECT_ID",
    "FIREBASE_SERVICE_ACCOUNT_JSON"
]

def validate_env():
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing and os.getenv("ENVIRONMENT") == "production":
        logger.error(f"CRITICAL: Missing environment variables: {', '.join(missing)}")
        exit(1)

validate_env()

# ── Lifespan & App ──────────────────────────────────
from backend.firestore_db import db as firestore_db # type: ignore
from backend.redis_client import HAS_REDIS, REDIS_URL # type: ignore

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LEVI Gateway...")
    try:
        firestore_db.collection("health_check").document("status").get(timeout=5.0)
        logger.info("Firestore connection verified.")
        
        # Cleanup zombie tasks
        zombie_jobs = firestore_db.collection("jobs") \
            .where("status", "==", "processing").get()
        for doc in zombie_jobs:
            doc.reference.update({
                "status": "failed", 
                "error": "Server restarted during processing",
                "completed_at": datetime.utcnow()
            })
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        if os.getenv("ENVIRONMENT") == "production": raise RuntimeError("STARTUP FAIL")
    yield

app = FastAPI(
    title="LEVI API Gateway",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs"
)

@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    """Strip /api/v1 prefix for consistency (needed for root routes)."""
    path = request.scope["path"]
    if path.startswith("/api/v1"):
        new_path = path[len("/api/v1"):] or "/"
        request.scope["path"] = new_path
        if "raw_path" in request.scope:
            request.scope["raw_path"] = new_path.encode()
    return await call_next(request)

# ── Middleware ──────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL if HAS_REDIS else "memory://")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def add_request_tracking(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    
    logger.info("gateway_request_completed", extra={
        "request_id": request_id, 
        "method": request.method,
        "path": request.url.path, 
        "status_code": response.status_code,
        "duration_ms": int(duration)
    })
    return response

# CORS
origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "https://levi-ai.vercel.app",
    "https://levi-ai.create.app",
    "https://levi-ai-c23c6.web.app",
    "https://levi-ai.cr",
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

# ── Routers ─────────────────────────────────────────
from backend.services.auth.router import router as auth_router # type: ignore
from backend.services.chat.router import router as chat_router # type: ignore
from backend.services.studio.router import router as studio_router # type: ignore
from backend.services.gallery.router import router as gallery_router # type: ignore
from backend.services.analytics.router import router as analytics_router # type: ignore
from backend.payments import router as payments_router # type: ignore

app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(studio_router, prefix="/api/v1")
app.include_router(gallery_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")

# ── Legacy/Global Routes ────────────────────────────
@app.get("/")
async def root():
    return {
        "status": "ok", 
        "service": "LEVI Gateway", 
        "version": "3.0.0",
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
        "auth": "ok",
    }
    
    try:
        # Ping the health_check collection
        firestore_db.collection("health_check").document("status").get(timeout=3.0)
        status_info["database"] = "ok"
    except Exception as e:
        logger.error(f"Health Check: Firestore unreachable: {e}")
        status_info["database"] = "error"
        status_info["status"] = "error"
        
    return status_info
