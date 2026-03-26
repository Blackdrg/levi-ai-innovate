# pyright: reportMissingImports=false

from fastapi import FastAPI, Depends, HTTPException, status, Request, Response  # type: ignore
from starlette.middleware.sessions import SessionMiddleware  # type: ignore
from starlette.routing import Route  # type: ignore

from fastapi.middleware.cors import CORSMiddleware  # type: ignore

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm  # type: ignore

from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse  # type: ignore

from sqlalchemy.orm import Session  # type: ignore
from sqlalchemy import text # type: ignore

from pydantic import BaseModel, Field, validator  # type: ignore

# from jose import JWTError, jwt # type: ignore

# from passlib.context import CryptContext # type: ignore

from datetime import datetime, timedelta, date

from slowapi import Limiter  # type: ignore

from slowapi.util import get_remote_address  # type: ignore

from slowapi.errors import RateLimitExceeded  # type: ignore

from slowapi import _rate_limit_exceeded_handler  # type: ignore
from authlib.integrations.starlette_client import OAuth # type: ignore
import os
from dotenv import load_dotenv
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()
import sentry_sdk  # type: ignore

import logging
import json
from pythonjsonlogger.json import JsonFormatter  # type: ignore
import time
import uuid
import hmac
import hashlib

# Structured JSON logging
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

logger = logging.getLogger(__name__)
logHandler = logging.StreamHandler()
formatter = CustomJsonFormatter(fmt='%(timestamp)s %(level)s %(name)s %(message)s')  # type: ignore
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
logger.propagate = False # Prevent double logging

def _safe_truncate(text: str, limit: int = 60) -> str:
    """Safe character-based truncation to bypass strict type-checker slicing errors."""
    if not text: return ""
    res = ""
    for i, char in enumerate(text):
        if i >= limit: break
        res += char
    return res

# Sentry Initialization
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of transactions.
        profiles_sample_rate=1.0,
        enable_tracing=True,
        environment=os.getenv("ENVIRONMENT", "production"),
        send_default_pii=True, # Enable data like request headers and IP
    )
    logger.info("Sentry initialized with performance monitoring.")

# ─────────────────────────────────────────────────────────────
# Environment Validation
# ─────────────────────────────────────────────────────────────
REQUIRED_ENV_VARS = [
    "SECRET_KEY",
    "DATABASE_URL",
    "RAZORPAY_KEY_ID",
    "RAZORPAY_KEY_SECRET",
    "RAZORPAY_WEBHOOK_SECRET",
    "ADMIN_KEY"
]

def validate_env():
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    is_prod = os.getenv("ENVIRONMENT") == "production"

    if missing:
        error_msg = f"CRITICAL: Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        if is_prod:
            raise RuntimeError(error_msg)
        else:
            print(f"\n[WARNING] {error_msg}\n")

    # ── SECRET_KEY entropy guard ─────────────────────────────────────────────
    # A short or guessable key allows JWT forgery. Require at least 32 raw bytes.
    # Generate a safe key with: python -c "import secrets; print(secrets.token_hex(32))"
    _secret = os.getenv("SECRET_KEY", "")
    if len(_secret.encode()) < 32:
        raise RuntimeError(
            "SECRET_KEY must be at least 32 bytes. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

validate_env()
# ─────────────────────────────────────────────────────────────

try:
    from backend.db import SessionLocal, engine, get_db, DATABASE_URL  # type: ignore
    from backend.models import Quote, Analytics, FeedItem, Base, Users, UserMemory, ChatHistory, PushSubscription, PaymentEvent  # type: ignore
    from backend.embeddings import embed_text, cosine_sim, HAS_MODEL  # type: ignore
    from backend.redis_client import (  # type: ignore
        get_cached_search, cache_search, get_conversation, save_conversation, 
        HAS_REDIS, REDIS_URL, cache_quote_embedding, get_cached_embedding
    )
    from backend.generation import generate_quote, generate_response  # type: ignore
    from backend.image_gen import generate_quote_image  # type: ignore
    from backend.video_gen import generate_quote_video  # type: ignore
    from backend.email_service import send_daily_quote, send_payment_receipt  # type: ignore
    from backend.payments import router as payments_router, use_credits, verify_payment_signature, verify_razorpay_signature, upgrade_user_tier  # type: ignore
    from backend.tasks import generate_video_task as generate_video_async  # type: ignore
    from backend.learning import (  # type: ignore
        collect_training_sample, UserPreferenceModel,
        AdaptivePromptManager, get_learning_stats, infer_implicit_feedback
    )
    from backend.trainer import trigger_training_pipeline, get_model_history, get_active_model_id, generate_with_active_model  # type: ignore
    from backend.training_models import TrainingData, ResponseFeedback, ModelVersion, TrainingJob  # type: ignore
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Could not import from backend.*: {e}. Falling back to local imports.")
    try:
        from db import SessionLocal, engine, get_db, DATABASE_URL  # type: ignore
        from models import Quote, Analytics, FeedItem, Base, Users, UserMemory, ChatHistory, PushSubscription, PaymentEvent  # type: ignore
        from embeddings import embed_text, cosine_sim, HAS_MODEL  # type: ignore
        from redis_client import (  # type: ignore
            get_cached_search, cache_search, get_conversation, save_conversation, 
            HAS_REDIS, REDIS_URL, cache_quote_embedding, get_cached_embedding
        )
        from generation import generate_quote, generate_response  # type: ignore
        from image_gen import generate_quote_image  # type: ignore
        from video_gen import generate_quote_video  # type: ignore
        from email_service import send_daily_quote, send_payment_receipt  # type: ignore
        from payments import router as payments_router, use_credits, verify_payment_signature, verify_razorpay_signature, upgrade_user_tier  # type: ignore
        from tasks import generate_video_task as generate_video_async  # type: ignore
        from learning import (  # type: ignore
            collect_training_sample, UserPreferenceModel,
            AdaptivePromptManager, get_learning_stats, infer_implicit_feedback
        )
        from trainer import trigger_training_pipeline, get_model_history, get_active_model_id, generate_with_active_model  # type: ignore
        from training_models import TrainingData, ResponseFeedback, ModelVersion, TrainingJob  # type: ignore
    except (ImportError, ModuleNotFoundError) as e2:
        logger.error(f"Fallback imports also failed: {e2}")
        raise e2  # type: ignore

import numpy as np  # type: ignore
import hashlib
import base64
from io import BytesIO
from typing import List, Optional
from sqlalchemy import func  # type: ignore
import asyncio
from concurrent.futures import ThreadPoolExecutor

from backend.firestore_db import db as firestore_db, get_document, set_document, query_documents, add_document # type: ignore

_executor = ThreadPoolExecutor(max_workers=4)

SECRET_KEY = os.environ.get("SECRET_KEY", "fallback")
CLIENT_KEY = os.getenv("CLIENT_KEY")

import firebase_admin # type: ignore
from firebase_admin import auth as firebase_auth # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # type: ignore

if not firebase_admin._apps:
    cred = firebase_admin.credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

security = HTTPBearer()

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded_token = firebase_auth.verify_id_token(cred.credentials)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        if not uid: raise credentials_exception
        
        # Firestore-native user lookup
        users_ref = firestore_db.collection("users")
        user_docs = users_ref.where("email", "==", email).limit(1).get()
        
        if not list(user_docs):
            # Create user in Firestore if not exists
            base_username = email.split('@')[0] if email else f"user_{uid[:8]}"
            username = base_username
            
            # Check for username uniqueness in Firestore
            existing_usernames = users_ref.where("username", "==", username).limit(1).get()
            counter = 1
            while list(existing_usernames):
                username = f"{base_username}{counter}"
                existing_usernames = users_ref.where("username", "==", username).limit(1).get()
                counter += 1
            
            user_data = {
                "uid": uid,
                "username": username,
                "email": email,
                "created_at": datetime.utcnow(),
                "tier": "free",
                "credits": 10
            }
            users_ref.document(uid).set(user_data)
            return user_data
            
        user = list(user_docs)[0].to_dict()
        user["id"] = list(user_docs)[0].id
        return user
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise credentials_exception

async def get_current_user_optional(cred: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if not cred: return None
    try:
        decoded_token = firebase_auth.verify_id_token(cred.credentials)
        email = decoded_token.get("email")
        if not email: return None
        
        users_ref = firestore_db.collection("users")
        user_docs = users_ref.where("email", "==", email).limit(1).get()
        if not list(user_docs): return None
        
        user = list(user_docs)[0].to_dict()
        user["id"] = list(user_docs)[0].id
        return user
    except Exception:
        return None

async def verify_admin(request: Request):
    admin_key = os.getenv("ADMIN_KEY", "")
    provided_key = request.headers.get("X-Admin-Key", "")
    # Use constant-time comparison to prevent timing-based brute-force attacks.
    if not admin_key or not hmac.compare_digest(provided_key.encode(), admin_key.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized admin access")
    return True

class AdminAdjustCredits(BaseModel):
    user_id: int
    amount: int

class User(BaseModel):
    username: str = Field(..., max_length=100)

class UserIn(BaseModel):
    username: str = Field(..., max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    email: Optional[str] = Field(None, max_length=100)

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None  # included when the endpoint issues one

# Expanded prompt-injection blocklist — covers the most common jailbreak templates.
# Note: string matching is a lightweight first layer only. A dedicated LLM guard
# (e.g. Llama Guard, OpenAI moderation API) should be added before production.
_INJECTION_PATTERNS = [
    "ignore previous", "ignore above", "ignore all previous",
    "forget previous", "new persona", "pretend you are",
    "system:", "assistant:", "user:",
    "jailbreak", "disregard", "override previous",
]

class Query(BaseModel):
    text: str = Field(..., max_length=500)
    author: Optional[str] = Field(None, max_length=100)
    mood: Optional[str] = Field(None, max_length=50)
    topic: Optional[str] = Field(None, max_length=50)
    lang: Optional[str] = Field("en", max_length=10)
    custom_bg: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)

    @validator("text", "author", "mood", "topic")
    def sanitize_text(cls, v):
        if v is None:
            return v
        v_lower = v.lower()
        for pattern in _INJECTION_PATTERNS:
            if pattern in v_lower:
                raise ValueError(f"Potential prompt injection detected: {pattern}")
        return v

class ChatMessage(BaseModel):
    session_id: str = Field(..., max_length=100)
    message: str = Field(..., max_length=1000)
    lang: Optional[str] = Field("en", max_length=10)
    mood: Optional[str] = Field("", max_length=50)
    persona_id: Optional[int] = None # Added for custom personas

    @validator("message")
    def sanitize_message(cls, v):
        v_lower = v.lower()
        for pattern in _INJECTION_PATTERNS:
            if pattern in v_lower:
                raise ValueError(f"Potential prompt injection detected: {pattern}")
        return v

class PersonaCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: str = Field(..., max_length=2000)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_public: bool = True

    @validator("name", "description", "system_prompt")
    def sanitize_persona_inputs(cls, v):
        if v:
            v_lower = v.lower()
            for pattern in _INJECTION_PATTERNS:
                if pattern in v_lower:
                    raise ValueError(f"Potential prompt injection detected: {pattern}")
        return v

# Helper for per-user rate limiting
def get_user_or_ip(request: Request):
    # Try to get user from state (if set by some middleware or dependency)
    # But since dependencies run after rate limiting usually, we might need a custom key_func
    # For now, we'll use a simpler approach or stick to IP if user not yet identified
    # Alternatively, we can use the Authorization header as a key if present
    auth = request.headers.get("Authorization")
    if auth:
        return auth
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_or_ip)

is_prod = os.getenv("ENVIRONMENT") == "production"

app = FastAPI(
    title="LEVI Quotes API",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    
    logger.info("request_completed", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": int(duration + 0.5) # Round to nearest int instead of float formatting
    })
    
    return response

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # CSP mirrors vercel.json and covers API responses that are consumed by the browser.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none';"
    )
    return response

app.include_router(payments_router)

# Rate Limiter setup
from slowapi.errors import RateLimitExceeded  # type: ignore
from slowapi import _rate_limit_exceeded_handler  # type: ignore
from typing import Any, cast
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

# Ensure database tables are created
# Base.metadata.create_all(bind=engine) # Removed - using Alembic migrations instead



env_origins = os.getenv("CORS_ORIGINS", "").split(",")

origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:8080", "http://127.0.0.1:8080",
    "https://levi-git-main-daksh-mehats-projects.vercel.app",
    "https://levi-k8iuadcvd-daksh-mehats-projects.vercel.app",
    "https://levi-ai.vercel.app",
    "https://levi-ai-daksh-mehats-projects.vercel.app",
    "https://levi-ai.create.app",
    "https://levi-ai-create.com",
    "https://levi-ai-c23c6.web.app",
    "https://levi-ai-c23c6.firebaseapp.com",
]

for o in env_origins:
    origin = o.strip()
    if origin and origin != "*" and origin not in origins:
        origins.append(origin)

allow_all = os.getenv("CORS_ORIGINS", "").strip() == "*"

# SECURITY: allow_credentials=True is MANDATORY for httpOnly cookies.
# When allow_credentials=True, allow_origins MUST be a list of trusted domains, NOT ["*"].
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Request-ID"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting LEVI backend (Firestore-Native)...")

    if not HAS_REDIS:
        logger.warning("Redis unavailable — using in-memory fallback.")
    else:
        masked = REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL
        logger.info(f"Redis connected: {masked}")

    try:
        # Simple connectivity check for Firestore
        firestore_db.collection("health_check").document("status").get()
        logger.info("Firestore connection verified.")
    except Exception as e:
        logger.error(f"Error connecting to Firestore: {e}")

    logger.info(f"CLIENT_KEY: {'SET' if CLIENT_KEY else 'NOT SET'}")


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"status": "ok", "message": "LEVI backend is running", "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health():
    """
    Enhanced health check with dependency verification.
    """
    status_info: dict = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "firestore": "unhealthy",
            "redis": "unhealthy" if HAS_REDIS else "unavailable"
        }
    }
    
    # Check Firestore
    try:
        # Simple read to check connectivity
        firestore_db.collection("health_check").document("status").get()
        status_info["dependencies"]["firestore"] = "healthy"
    except Exception as e:
        logger.error(f"Health Check: Firestore unreachable: {e}")
        status_info["status"] = "error"

    # Check Redis
    if HAS_REDIS:
        try:
            from backend.redis_client import r  # type: ignore
            if r and r.ping():
                status_info["dependencies"]["redis"] = "healthy"
            else:
                status_info["status"] = "error"
        except Exception as e:
            logger.error(f"Health Check: Redis unreachable: {e}")
            status_info["status"] = "error"
            status_info["dependencies"]["redis"] = "unhealthy"

    if status_info["status"] != "ok":
        return JSONResponse(status_code=503, content=status_info)
        
    return status_info


class FallbackQuote:
    text = "The only true wisdom is in knowing you know nothing."
    author = "Socrates"

today_quote = FallbackQuote()

@app.get("/daily_quote")
def daily_quote():
    try:
        from backend.generation import fetch_open_source_quote  # type: ignore
    except ImportError:
        from generation import fetch_open_source_quote  # type: ignore

    os_quote = fetch_open_source_quote()
    if os_quote:
        return {"quote": os_quote['quote'], "author": os_quote['author']}


    return {"quote": today_quote.text, "author": today_quote.author}





@app.get("/analytics")
async def get_analytics():
    try:
        # For simplicity, we'll sum from the 'analytics' collection
        analytics_ref = firestore_db.collection("analytics")
        docs = analytics_ref.stream()
        
        total_chats = 0
        total_likes = 0
        total_users = 0
        
        for doc in docs:
            data = doc.to_dict()
            total_chats += data.get("chats_count", 0)
            total_likes += data.get("likes_count", 0)
            total_users += data.get("daily_users", 0)
            
    except Exception as e:
        logger.warning(f"Analytics query failed: {e}")
        total_chats = 0
        total_likes = 0
        total_users = 0

    return {
        "total_chats": total_chats,
        "daily_users": total_users,
        "popular_topics": ["philosophy", "success", "wisdom"], # Placeholder or implement top topics logic
        "likes_count": total_likes,
    }


@app.post("/search_quotes", response_model=List[dict])
def search_quotes(query: Query):
    query_hash = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()
    cached = get_cached_search(query_hash)
    if cached:
        return cached

    quotes_ref = firestore_db.collection("quotes")
    
    if not query.text:
        # Use simple limit for random-ish results
        docs = list(quotes_ref.limit(query.top_k).stream())
        results = [d.to_dict() for d in docs]
    elif not HAS_MODEL:
        # Keyword-ish fallback
        if query.mood:
            docs = list(quotes_ref.where("mood", "==", query.mood).limit(100).stream())
        else:
            docs = list(quotes_ref.limit(100).stream())
            
        results = [d.to_dict() for d in docs if query.text.lower() in d.to_dict().get("text", "").lower()]
        if not results:
            results = [d.to_dict() for d in docs[:query.top_k]]
    else:
        query_embedding = embed_text(query.text)
        # Stream and score (Naive Vector Search)
        if query.mood:
            docs = list(quotes_ref.where("mood", "==", query.mood).limit(200).stream())
        else:
            docs = list(quotes_ref.limit(200).stream())
            
        q_emb = np.array(query_embedding)
        scored = []
        for d in docs:
            data = d.to_dict()
            emb = data.get("embedding")
            if emb:
                score = cosine_sim(q_emb, np.array(emb))
                scored.append((data, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        results = [s[0] for s in scored[:query.top_k]]

    formatted = [
        {"quote": q.get("text"), "author": q.get("author"), "topic": q.get("topic"), "mood": q.get("mood"),
         "similarity": 0.9,
         "search_mode": "semantic" if HAS_MODEL else "keyword"}
        for q in results
    ]

    cache_search(query_hash, formatted)
    return formatted





@app.post("/generate")

def gen_quote(prompt: Query):

    generated = generate_quote(prompt.text, mood=prompt.mood or "")

    return {"generated_quote": generated}


# ── Content Engine: Unified Content Generator ────────────────────────────────

class ContentRequest(BaseModel):
    type: str           # quote, essay, story, script, philosophy, caption, thread, blog
    topic: str
    tone: str = "inspiring"
    depth: str = "high"  # low, medium, high


@app.post("/generate_content")
@limiter.limit("5/minute")
async def gen_content(
    request: Request,
    req: ContentRequest,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    """Generate content of any type (quote, essay, story, script, etc.)."""
    # Cost protection
    from backend.redis_client import get_daily_ai_spend, incr_daily_ai_spend  # type: ignore
    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily AI usage limit reached.")
    incr_daily_ai_spend(1.0)

    # Credit check for non-quote types
    if req.type != "quote" and current_user:
        from backend.payments import use_credits  # type: ignore
        use_credits(current_user.id, amount=1, db=db)

    try:
        from backend.content_engine import generate_content  # type: ignore
    except ImportError:
        from content_engine import generate_content  # type: ignore

    result = generate_content(
        content_type=req.type,
        topic=req.topic,
        tone=req.tone,
        depth=req.depth,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/content_types")
async def list_content_types():
    """Return available content types and tones."""
    try:
        from backend.content_engine import get_available_types, get_available_tones  # type: ignore
    except ImportError:
        from content_engine import get_available_types, get_available_tones  # type: ignore
    return {"types": get_available_types(), "tones": get_available_tones()}


@app.get("/image_styles")
async def list_image_styles():
    """Return available image generation styles."""
    try:
        from backend.sd_engine import get_available_styles  # type: ignore
    except ImportError:
        from sd_engine import get_available_styles  # type: ignore
    return {"styles": get_available_styles()}





@app.post("/generate_image")
@limiter.limit("5/minute")
async def gen_image(request: Request, req: Query, current_user: Optional[dict] = Depends(get_current_user_optional)):
    try:
        # ── Cost Protection Layer ──────────────────────────
        from backend.redis_client import get_daily_ai_spend, incr_daily_ai_spend  # type: ignore
        daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
        if get_daily_ai_spend() >= daily_limit:
            raise HTTPException(status_code=429, detail="Daily AI usage limit reached. Try again tomorrow.")
        incr_daily_ai_spend(1.0)

        user_id = current_user.get("uid") if current_user else None
        user_tier = current_user.get("tier", "free") if current_user else "free"
        
        # Security: Validate custom_bg if provided
        if req.custom_bg:
            # Check size (approximate for base64)
            if len(req.custom_bg) > 7 * 1024 * 1024: # type: ignore # ~5MB after decoding
                raise HTTPException(status_code=400, detail="Custom background exceeds 5MB limit")
            
            # Basic type check
            allowed_types = ["data:image/jpeg", "data:image/png", "data:image/webp"]
            if not any(req.custom_bg.startswith(t) for t in allowed_types): # type: ignore
                raise HTTPException(status_code=400, detail="Invalid image format. Only JPEG, PNG and WEBP are allowed.")
        
        # Check if we should use Celery for async processing
        USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

        if USE_CELERY:
            from backend.tasks import generate_image_task  # type: ignore
            task = generate_image_task.delay(
                req.text, 
                req.author or "Unknown",
                req.mood or "neutral",
                user_id,
                user_tier
            )
            # Credit System: Deduct AFTER successful dispatch
            if current_user:
                from backend.payments import use_credits  # type: ignore
                use_credits(user_id, amount=1)
                logger.info(f"Deducted 1 credit for user {user_id} after task dispatch")

            return JSONResponse(status_code=202, content={"task_id": task.id, "status": "processing", "message": "Image generation started in background."})

        loop = asyncio.get_event_loop()
        bio = await loop.run_in_executor(
            _executor,
            lambda: generate_quote_image( # type: ignore
                req.text, 
                author=req.author or "Unknown",
                mood=req.mood or "neutral", 
                custom_bg=req.custom_bg or "",
                user_tier=user_tier
            ),
        )

        img_b64 = base64.b64encode(bio.getvalue()).decode()
        img_data = f"data:image/png;base64,{img_b64}"

        # Save to Firestore
        feed_ref = firestore_db.collection("feed_items")
        new_feed_data = {
            "user_id": user_id,
            "text": req.text,
            "author": req.author or "Unknown",
            "mood": req.mood or "neutral",
            "image_b64": img_data,
            "likes": 0,
            "timestamp": datetime.utcnow()
        }
        update_time, doc_ref = feed_ref.add(new_feed_data)
        return {"id": doc_ref.id, "image_b64": img_data}

    except Exception as e:
        import traceback
        logger.error(f"Image generation error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_video")
@limiter.limit("2/minute")
async def gen_video(request: Request, req: Query, current_user: Optional[dict] = Depends(get_current_user_optional)):
    """Generate or queue video generation for a quote."""
    try:
        from backend.redis_client import get_daily_ai_spend, incr_daily_ai_spend  # type: ignore
        daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
        if get_daily_ai_spend() >= daily_limit:
            raise HTTPException(status_code=429, detail="Daily AI usage limit reached. Try again tomorrow.")
        incr_daily_ai_spend(2.0)

        user_id = current_user.get("uid") if current_user else None
        user_tier = current_user.get("tier", "free") if current_user else "free"

        USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"

        if USE_CELERY:
            from backend.tasks import generate_video_task  # type: ignore
            task = generate_video_task.delay(
                req.text,
                req.author or "Unknown",
                req.mood or "neutral",
                user_id,
                user_tier
            )
            if current_user:
                from backend.payments import use_credits  # type: ignore
                # user_id here is the uid string
                use_credits(user_id, amount=2)
                logger.info(f"Deducted 2 credits for user {user_id} after task dispatch")

            return JSONResponse(status_code=202, content={"task_id": task.id, "status": "processing", "message": "Video generation started in background."})

        loop = asyncio.get_event_loop()
        video_bytes_io = await loop.run_in_executor(
            _executor,
            lambda: generate_quote_video(
                req.text,
                req.author or "Unknown",
                req.mood or "neutral",
                user_tier
            )
        )
        
        # Upload to s3 if available, or error since video is too large for inline responses
        if os.getenv("AWS_S3_BUCKET"):
             from backend.tasks import upload_video_to_s3 # type: ignore
             video_url = upload_video_to_s3(video_bytes_io.getvalue(), user_id)
             return {"status": "done", "url": video_url}
        else:
             raise HTTPException(status_code=400, detail="Celery required for video or AWS S3 must be configured.")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Video generation error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/like/{item_type}/{item_id}")
async def like_item(item_type: str, item_id: str):
    try:
        if item_type == "quote":
            collection = "quotes"
        elif item_type == "feed":
            collection = "feed_items"
        else:
            raise HTTPException(status_code=400, detail="Invalid item type")

        item_ref = firestore_db.collection(collection).document(item_id)
        item_doc = item_ref.get()

        if not item_doc.exists:
            raise HTTPException(status_code=404, detail="Item not found")

        # Atomic increment for likes
        from google.cloud import firestore # type: ignore
        item_ref.update({"likes": firestore.Increment(1)})
        
        # Update analytics
        today_str = date.today().isoformat()
        analytics_ref = firestore_db.collection("analytics").document(today_str)
        analytics_doc = analytics_ref.get()
        
        if analytics_doc.exists:
            analytics_ref.update({"likes_count": firestore.Increment(1)})
        else:
            analytics_ref.set({"date": today_str, "likes_count": 1, "chats_count": 0, "daily_users": 0})

        # Return updated likes (requires a re-fetch or just incrementing the cached value)
        new_likes = (item_doc.to_dict().get("likes", 0)) + 1
        return {"status": "success", "new_likes": new_likes}
    except Exception as e:
        logger.error(f"Like error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feed", response_model=List[dict])
async def get_feed(limit: int = 20, offset: int = 0):
    try:
        feed_ref = firestore_db.collection("feed_items")
        # Note: Firestore offset is expensive (skips items), but for small feeds it's okay.
        # Better to use cursor-based pagination for large feeds.
        query = feed_ref.order_by("timestamp", direction=firestore_db.DESCENDING).limit(limit).offset(offset)
        docs = query.get()
        
        results = []
        for doc in docs:
            d = doc.to_dict()
            results.append({
                "id": doc.id,
                "text": d.get("text"),
                "author": d.get("author"),
                "mood": d.get("mood"),
                "image": d.get("image_url") or d.get("image_b64"),
                "likes": d.get("likes", 0),
                "time": d.get("timestamp").isoformat() if d.get("timestamp") else None
            })
        return results
    except Exception as e:
        logger.error(f"Feed error: {e}")
        return []





@app.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    msg: ChatMessage,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = current_user.get("uid") if current_user else None
    msg_text_snip = _safe_truncate(str(msg.message), 60)
    logger.info(f"Chat [{msg.session_id}] (User: {user_id}): '{msg_text_snip}'")

    # ── Cost Protection Layer ──────────────────────────
    from backend.redis_client import get_daily_ai_spend, incr_daily_ai_spend  # type: ignore
    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily AI usage limit reached. Try again tomorrow.")
    incr_daily_ai_spend(1.0)

    # Analytics
    try:
        from google.cloud import firestore # type: ignore
        today_str = date.today().isoformat()
        analytics_ref = firestore_db.collection("analytics").document(today_str)
        if not analytics_ref.get().exists:
            analytics_ref.set({"date": today_str, "chats_count": 1, "likes_count": 0, "daily_users": 1})
        else:
            analytics_ref.update({"chats_count": firestore.Increment(1)})
    except Exception as e:
        logger.warning(f"Analytics update failed: {e}")

    # User memory — Redis-cached (TTL = 10 min)
    user_mem = None
    if user_id:
        from backend.redis_client import get_cached_user_memory, cache_user_memory  # type: ignore
        cached = get_cached_user_memory(user_id)
        
        memory_ref = firestore_db.collection("user_memory").document(user_id)
        if cached:
            user_mem_data = cached
        else:
            memory_doc = memory_ref.get()
            if memory_doc.exists:
                user_mem_data = memory_doc.to_dict()
            else:
                user_mem_data = {"user_id": user_id, "mood_history": [], "liked_topics": [], "interaction_count": 0}
                memory_ref.set(user_mem_data)
        
        user_mem_data["interaction_count"] = user_mem_data.get("interaction_count", 0) + 1
        
        # Update Firestore and cache
        memory_ref.update({"interaction_count": user_mem_data["interaction_count"]})
        cache_user_memory(user_id, user_mem_data)

    # Load history
    history = get_conversation(msg.session_id)

    # Infer implicit feedback from previous turn
    try:
        try:
            from backend.learning import infer_implicit_feedback, collect_training_sample # type: ignore
        except ImportError:
            def infer_implicit_feedback(*args, **kwargs): return None
            def collect_training_sample(*args, **kwargs): return None
        implicit_rating = infer_implicit_feedback(history, msg.message)
        if implicit_rating and len(history) >= 1:
            prev = history[-1]
            collect_training_sample(
                user_message=prev.get("user", ""),
                bot_response=prev.get("bot", ""),
                mood=msg.mood or "philosophical",
                rating=implicit_rating,
                session_id=msg.session_id,
                user_id=user_id,
            )
    except Exception as e:
        logger.warning(f"Implicit feedback collection failed: {e}")

    # ── Router Agent: Multi-Agent System ──────────────────────────
    try:
         from backend.agents import RouterAgent  # type: ignore
         router = RouterAgent()
         classification = router.classify_intent(msg.message)
         intent = classification.get("intent", "chat")
         params = classification.get("parameters", {})

         if intent in ["generate_image", "generate_video", "generate_content"]:
              credits_needed = 2 if intent == "generate_video" else 1
              if current_user:
                   try:
                        from backend.payments import use_credits  # type: ignore
                        use_credits(user_id, amount=credits_needed)
                   except HTTPException as he:
                        return {"response": f"❌ [Router] Credits exhausted. {he.detail}"}
                   except Exception:
                        return {"response": "❌ [Router] Credit check failed."}

              if intent == "generate_image":
                   from backend.tasks import generate_image_task  # type: ignore
                   generate_image_task.delay(params.get("topic") or msg.message, "Unknown", msg.mood or "neutral", user_id, current_user.tier if current_user else "free")
                   return {"response": f"🎨 [Visual Agent] I am generating an image for '{params.get('topic') or msg.message}'. Check your Feed shortly!"}

              if intent == "generate_video":
                   from backend.tasks import generate_video_task  # type: ignore
                   generate_video_task.delay(params.get("topic") or msg.message, "Unknown", msg.mood or "neutral", user_id, current_user.tier if current_user else "free")
                   return {"response": f"🎥 [Video Agent] Video synthesis started for '{params.get('topic') or msg.message}'. This will appear in your Feed when ready."}

              if intent == "generate_content":
                   from backend.content_engine import generate_content  # type: ignore
                   c_type = params.get("content_type", "essay")
                   result = generate_content(content_type=c_type, topic=params.get("topic") or msg.message)
                   if "content" in result:
                        return {"response": f"✍️ [Content Agent] Here is your {c_type}:\n\n{result['content']}"}
                   return {"response": f"❌ [Content Agent] Failed to generate {c_type}."}
    except Exception as e:
         logger.warning(f"RouterAgent failed: {e}")
         # Graceful fallback to normal chat flow

    # Build personalised system prompt
    personalized_system = None
    try:
        from backend.learning import UserPreferenceModel, AdaptivePromptManager  # type: ignore
        base = AdaptivePromptManager().get_best_variant(msg.mood or "philosophical")
        
        # ─── Load Custom Persona ───
        if msg.persona_id:
            persona_doc = firestore_db.collection("personas").document(msg.persona_id).get()
            if persona_doc.exists:
                base = persona_doc.to_dict().get("system_prompt", base)

        if user_id:
            pref = UserPreferenceModel(user_id)
            personalized_system = pref.build_system_prompt(base, msg.mood or "philosophical")
        else:
            personalized_system = base
    except Exception as e:
        logger.warning(f"Failed to build personalised prompt: {e}")

    # ── Vector Memory Retrieval ──
    if user_id:
        try:
            from backend.embeddings import embed_text, cosine_sim  # type: ignore
            import numpy as np
            q_emb = embed_text(msg.message)
            
            # Simple Firestore retrieval + in-memory similarity (until Vector Search)
            mem_ref = firestore_db.collection("user_memory_logs").where("user_id", "==", user_id)
            docs = mem_ref.limit(50).get() # cap search space
            
            scored = []
            for doc in docs:
                m = doc.to_dict()
                if m.get("embedding"):
                    scored.append((m, cosine_sim(np.array(q_emb), np.array(m["embedding"]))))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            past_mem = [s[0] for i, s in enumerate(scored) if i < 3]

            if past_mem:
                 memory_context = "\n\n[Relevant past memories]:\n" + "\n".join([f"- User: {m.get('text')}\n  LEVI: {m.get('response')}" for m in past_mem if m.get('response')])
                 if personalized_system:
                      personalized_system = personalized_system + memory_context
                 else:
                      personalized_system = memory_context
        except Exception as e:
             logger.warning(f"Vector memory retrieval failed: {e}")

    # AI Generation
    try:
        from backend.trainer import generate_with_active_model  # type: ignore
        bot_response = generate_with_active_model(
            prompt=msg.message,
            system_prompt=personalized_system or "You are LEVI, a philosophical AI muse.",
            max_tokens=150,
        )
        if not bot_response:
            raise ValueError("Empty response")
    except Exception:
        bot_response = generate_response(
            msg.message,
            history=history,
            mood=msg.mood or "",
            lang=msg.lang or "en",
        )

    # Store turn for training
    try:
        from backend.learning import collect_training_sample  # type: ignore
        collect_training_sample(
            user_message=msg.message,
            bot_response=bot_response,
            mood=msg.mood or "philosophical",
            rating=None,
            session_id=msg.session_id,
            user_id=user_id,
        )
    except Exception as e:
        logger.warning(f"Training data collection failed: {e}")

    # Save history
    history.append({"user": msg.message, "bot": bot_response})
    save_conversation(msg.session_id, history, user_id=user_id)

    # ── Vector Memory Storage ──
    if user_id:
        try:
            from backend.embeddings import embed_text  # type: ignore
            emb_to_save = embed_text(msg.message)
            
            firestore_db.collection("user_memory_logs").add({
                "user_id": user_id,
                "text": msg.message,
                "response": bot_response,
                "embedding": emb_to_save,
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.warning(f"Vector memory storage failed: {e}")

    return {"response": bot_response}

# ── Learning: Explicit Feedback ──────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    session_id: str
    message_hash: str
    rating: int                 # 1-5
    bot_response: str
    user_message: str
    mood: Optional[str] = "philosophical"
    feedback_type: str = "star"

@app.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    User rates a response 1-5 in Firestore.
    """
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    user_id = current_user.get("uid") if current_user else None

    try:
        from backend.learning import collect_training_sample  # type: ignore

        # Store training sample (upsert if exists via fingerprint or just add new)
        sample_id = collect_training_sample(
            user_message=req.user_message,
            bot_response=req.bot_response,
            mood=req.mood or "philosophical",
            rating=req.rating,
            session_id=req.session_id,
            user_id=user_id,
        )

        # Store explicit feedback record in Firestore
        firestore_db.collection("response_feedback").add({
            "training_data_id": sample_id,
            "user_id": user_id,
            "session_id": req.session_id,
            "message_hash": req.message_hash,
            "rating": req.rating,
            "feedback_type": req.feedback_type,
            "created_at": datetime.utcnow()
        })

        return {"status": "success", "sample_id": sample_id, "rating": req.rating}

    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")


# ── Learning: Get personalised system prompt preview ─────────────────────────
@app.get("/learning/my_profile")
async def get_my_learning_profile(
    current_user: dict = Depends(get_current_user),
):
    """Returns the AI's current learned profile for this user from Firestore."""
    from backend.learning import UserPreferenceModel  # type: ignore
    uid = current_user.get("uid")
    model = UserPreferenceModel(uid)
    profile = model.get_profile()
    return {
        "user_id": uid,
        "profile": profile,
        "system_prompt_preview": model.build_system_prompt(
            "You are LEVI, a philosophical AI.", "philosophical"
        )[:200] + "...",
    }


# ── Learning: Admin stats ─────────────────────────────────────────────────────
@app.get("/learning/stats")
async def get_learning_stats_route(
    current_user: dict = Depends(get_current_user),
):
    """Returns learning system statistics via Firestore. Admin-level endpoint."""
    if current_user.get("tier") not in ("creator", "admin"):
         raise HTTPException(status_code=403, detail="Requires admin access")
    from backend.learning import get_learning_stats  # type: ignore
    stats = get_learning_stats()
    return stats


# ── Training: Model history ───────────────────────────────────────────────────
@app.get("/model/versions")
async def get_model_versions(
    current_user: dict = Depends(get_current_user),
):
    """Returns all fine-tuned model versions from Firestore."""
    from backend.trainer import get_model_history, get_active_model_id  # type: ignore
    versions = get_model_history()
    return {
        "active_model": get_active_model_id() or "groq/llama-3.1-8b-instant (base)",
        "versions": versions,
    }


# ── Training: Manually trigger a training run (admin only) ───────────────────
@app.post("/model/trigger_training")
async def trigger_training_manually(
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger a fine-tuning run via Firestore. Admin use only."""
    # Basic admin check: only creator-tier users can trigger training
    if current_user.get("tier") not in ("creator", "admin"):
        raise HTTPException(status_code=403, detail="Requires creator tier")

    from backend.trainer import trigger_training_pipeline  # type: ignore
    task = trigger_training_pipeline.delay()
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Training pipeline queued. Check /task_status/{task_id} for progress.",
    }


# ── Training: Current model status ───────────────────────────────────────────
@app.get("/model/status")
async def get_model_status():
    """Public endpoint: returns which model is powering LEVI right now."""
    from trainer import get_active_model_id  # type: ignore
    from learning import get_learning_stats  # type: ignore

    active = get_active_model_id()
    stats  = get_learning_stats()

    # Latest training job from Firestore
    jobs_ref = firestore_db.collection("training_jobs")
    latest_jobs = jobs_ref.order_by("created_at", direction=firestore_db.DESCENDING).limit(1).get()
    latest_job = latest_jobs[0].to_dict() if latest_jobs else None

    return {
        "active_model": active or "groq/llama-3.1-8b-instant",
        "is_fine_tuned": active is not None,
        "training_samples_collected": stats["total_training_samples"],
        "knowledge_base_entries":     stats["learned_quotes"],
        "latest_training_job": {
            "status": latest_job.get("status", "none"),
            "created_at": latest_job.get("created_at").isoformat() if latest_job.get("created_at") else None,
        } if latest_job else None,
    }
@app.get("/export_my_data")
async def export_my_data(current_user: dict = Depends(get_current_user)):
    """
    GDPR Compliance: Export all data associated with the current user via Firestore.
    """
    try:
        uid = current_user.get("uid")
        
        # Fetch chat history from sessions
        convs = firestore_db.collection("conversations").where("user_id", "==", uid).get()
        chats = []
        for c in convs:
            chats.extend(c.to_dict().get("history", []))
        
        # Fetch feed items (generations)
        items = firestore_db.collection("feed_items").where("user_id", "==", uid).get()
        item_data = [i.to_dict() for i in items]
        
        export = {
            "profile": current_user,
            "chats": chats,
            "generations": item_data,
            "exported_at": datetime.utcnow().isoformat()
        }
        
        return export
    except Exception as e:
        logger.error(f"Data export failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data.")

@app.delete("/delete_account")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """
    GDPR/Legal Compliance: Delete user account and associated data from Firestore.
    """
    try:
        uid = current_user.get("uid")
        
        # Delete conversations
        convs = firestore_db.collection("conversations").where("user_id", "==", uid).get()
        for c in convs: c.reference.delete()
        
        # Delete memory
        firestore_db.collection("user_memory").document(uid).delete()
        firestore_db.collection("user_memory_logs").where("user_id", "==", uid).get() # Needs batch delete logic or similar
        # Add deletion for user_memory_logs
        m_logs = firestore_db.collection("user_memory_logs").where("user_id", "==", uid).get()
        for l in m_logs: l.reference.delete()
        
        # Anonymize feed items
        items = firestore_db.collection("feed_items").where("user_id", "==", uid).get()
        for i in items: i.reference.update({"user_id": None})
        
        # Delete user
        firestore_db.collection("users").document(uid).delete()
        
        logger.info(f"Account deleted in Firestore for user: {uid}")
        return {"status": "success", "message": "Account and all personal data deleted."}
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account.")

@app.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return current_user

# Phase 2: Viral Loops & Engagement

@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check the status of a Celery background task.
    """
    from backend.tasks import celery_app  # type: ignore
    from celery.result import AsyncResult  # type: ignore
    
    res = AsyncResult(task_id, app=celery_app)
    if res.ready():
        result = res.result
        # If result is a dict with status='failed', surface it
        if isinstance(result, dict) and result.get("status") == "failed":
            return {
                "status": "failed",
                "error": result.get("error")
            }
        
        return {
            "status": "completed",
            "result": result
        }
    
    # Check if task failed at celery level
    if res.status == 'FAILURE':
        return {
            "status": "failed",
            "error": str(res.result)
        }
        
    return {"status": "pending"}

@app.post("/track_share")
async def track_share(current_user: dict = Depends(get_current_user)):
    """
    Track when a user shares content. Reward them after 5 shares in Firestore.
    """
    uid = current_user.get("uid")
    user_ref = firestore_db.collection("users").document(uid)
    
    from google.cloud import firestore # type: ignore
    user_ref.update({"share_count": firestore.Increment(1)})
    
    # Logic for reward: we use the value from current_user + 1
    new_shares = current_user.get("share_count", 0) + 1
    rewarded = False
    bonus_credits = current_user.get("bonus_credits", 0)
    
    if new_shares > 0 and new_shares % 5 == 0:
        user_ref.update({"bonus_credits": firestore.Increment(10)})
        rewarded = True
        bonus_credits += 10
        
    return {
        "status": "success", 
        "share_count": new_shares, 
        "rewarded": rewarded,
        "bonus_credits": bonus_credits
    }

@app.get("/my_gallery")
async def get_my_gallery(current_user: dict = Depends(get_current_user), limit: int = 20, offset: int = 0):
    """Fetch all generated items for the current user from Firestore."""
    uid = current_user.get("uid")
    try:
        feed_ref = firestore_db.collection("feed_items")
        query = feed_ref.where("user_id", "==", uid).order_by("timestamp", direction=firestore_db.DESCENDING).limit(limit).offset(offset)
        docs = query.get()
        
        results = []
        for doc in docs:
            i = doc.to_dict()
            results.append({
                "id": doc.id,
                "text": i.get("text"),
                "author": i.get("author"),
                "mood": i.get("mood"),
                "image": i.get("image_url") or i.get("image_b64"),
                "video": i.get("video_url"),
                "likes": i.get("likes", 0),
                "time": i.get("timestamp").isoformat() if i.get("timestamp") else None
            })
        return results
    except Exception as e:
        logger.error(f"Gallery error: {e}")
        return []

# ─────────────────────────────────────────────────────────────
# Admin Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/admin/users")
@limiter.limit("5/minute")
async def admin_list_users(request: Request, _admin: bool = Depends(verify_admin)):
    try:
        users_ref = firestore_db.collection("users")
        docs = users_ref.order_by("created_at", direction=firestore_db.DESCENDING).get()
        
        results = []
        for doc in docs:
            u = doc.to_dict()
            results.append({
                "id": doc.id,
                "username": u.get("username") or u.get("email"),
                "email": u.get("email"),
                "tier": u.get("tier"),
                "credits": u.get("credits"),
                "is_verified": u.get("is_verified"),
                "created_at": u.get("created_at").isoformat() if u.get("created_at") else None
            })
        return results
    except Exception as e:
        logger.error(f"Admin users list error: {e}")
        return []

@app.get("/admin/feed")
@limiter.limit("5/minute")
async def admin_list_feed(request: Request, limit: int = 50, offset: int = 0, _admin: bool = Depends(verify_admin)):
    try:
        feed_ref = firestore_db.collection("feed_items")
        query = feed_ref.order_by("timestamp", direction=firestore_db.DESCENDING).limit(limit).offset(offset)
        docs = query.get()
        
        return [{
            "id": doc.id,
            "user_id": doc.to_dict().get("user_id"),
            "text": doc.to_dict().get("text"),
            "author": doc.to_dict().get("author"),
            "mood": doc.to_dict().get("mood"),
            "image_url": doc.to_dict().get("image_url"),
            "video_url": doc.to_dict().get("video_url"),
            "likes": doc.to_dict().get("likes"),
            "timestamp": doc.to_dict().get("timestamp").isoformat() if doc.to_dict().get("timestamp") else None
        } for doc in docs]
    except Exception as e:
        logger.error(f"Admin feed list error: {e}")
        return []

@app.delete("/admin/feed/{item_id}")
@limiter.limit("5/minute")
async def admin_delete_feed_item(request: Request, item_id: str, _admin: bool = Depends(verify_admin)):
    try:
        firestore_db.collection("feed_items").document(item_id).delete()
        return {"status": "success", "message": f"Item {item_id} deleted from Firestore"}
    except Exception as e:
        logger.error(f"Admin delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete item")

@app.post("/admin/adjust_credits")
@limiter.limit("5/minute")
async def admin_adjust_credits(request: Request, adj: AdminAdjustCredits, _admin: bool = Depends(verify_admin)):
    user_ref = firestore_db.collection("users").document(adj.user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    from google.cloud import firestore # type: ignore
    user_ref.update({"credits": firestore.Increment(adj.amount)})
    
    return {"status": "success", "new_credits": (user_doc.to_dict().get("credits", 0)) + adj.amount}

@app.get("/admin/payments")
@limiter.limit("5/minute")
async def admin_list_payments(request: Request, _admin: bool = Depends(verify_admin)):
    """
    In a real app, you might query a Payments table. 
    For now, we can check recent success logs or Redis idempotency keys.
    """
    # For now, return a placeholder or implement if a Payments table existed.
    return {"message": "Payment history can be viewed in Razorpay Dashboard for now."}

# ─────────────────────────────────────────────────────────────

@app.post("/test_daily_email")
async def test_daily_email(current_user: dict = Depends(get_current_user)):
    """
    Test sending a daily wisdom email to the current user via Firestore.
    """
    uid = current_user.get("uid")
    try:
        memory_doc = firestore_db.collection("user_memory").document(uid).get()
        user_mem = memory_doc.to_dict() if memory_doc.exists else {}
        
        topics = user_mem.get("liked_topics", ["wisdom"])
        mood = user_mem.get("mood_history", ["philosophical"])[-1] if user_mem.get("mood_history") else "philosophical"
        
        from backend.email_service import send_daily_quote # type: ignore
        success = send_daily_quote(
            user_email=current_user.get("email") or current_user.get("username"),
            user_name=(current_user.get("email") or "User").split('@')[0],
            liked_topics=topics,
            last_mood=mood
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email. Check API key.")
        
        return {"status": "success", "message": "Daily wisdom email sent!"}
    except Exception as e:
        logger.error(f"Test email failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get the current authenticated user's profile from Firestore.
    """
    return {
        "id": current_user.get("uid"),
        "username": current_user.get("username") or current_user.get("email"),
        "email": current_user.get("email"),
        "tier": current_user.get("tier"),
        "credits": current_user.get("credits"),
        "share_count": current_user.get("share_count"),
        "created_at": current_user.get("created_at").isoformat() if current_user.get("created_at") else None
    }

class OrderRequest(BaseModel):
    plan: str  # "pro" or "creator"

class PaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: Optional[str] = "pro"

class PushSubscriptionSchema(BaseModel):
    endpoint: str
    keys: dict

@app.get("/push/vapid_public_key")
async def get_vapid_public_key():
    return {"public_key": os.getenv("VAPID_PUBLIC_KEY")}

@app.post("/push/subscribe")
async def subscribe_push(sub: PushSubscriptionSchema, current_user: dict = Depends(get_current_user)):
    uid = current_user.get("uid")
    
    # Check if subscription already exists for this endpoint in Firestore
    subs_ref = firestore_db.collection("push_subscriptions")
    existing_docs = subs_ref.where("endpoint", "==", sub.endpoint).limit(1).get()
    
    p256dh = str(sub.keys.get("p256dh", ""))
    auth = str(sub.keys.get("auth", ""))
    
    if not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Invalid push subscription keys")

    if existing_docs:
        doc_ref = existing_docs[0].reference
        doc_ref.update({
            "user_id": uid,
            "p256dh": p256dh,
            "auth": auth,
            "updated_at": datetime.utcnow()
        })
    else:
        subs_ref.add({
            "user_id": uid,
            "endpoint": sub.endpoint,
            "p256dh": p256dh,
            "auth": auth,
            "created_at": datetime.utcnow()
        })
    
    return {"status": "success", "message": "Subscribed to push notifications in Firestore"}

@app.post("/push/send_test")
async def send_test_push(current_user: dict = Depends(get_current_user)):
    from backend.tasks import send_push_notification_task  # type: ignore
    uid = current_user.get("uid")
    
    subs = firestore_db.collection("push_subscriptions").where("user_id", "==", uid).get()
    if not subs:
        raise HTTPException(status_code=404, detail="No push subscriptions found for this user")
    
    for s_doc in subs:
        s = s_doc.to_dict()
        send_push_notification_task.delay(
            s_doc.id,
            s.get("endpoint"),
            s.get("p256dh"),
            s.get("auth"),
            "LEVI Wisdom",
            "This is a test notification from your daily wisdom guide. ✨"
        )
    return {"status": "success", "message": f"Sent {len(subs)} test notifications via Firestore"}

@app.post("/create_order")
async def new_order(req: OrderRequest, current_user: dict = Depends(get_current_user)):
    from backend.payments import create_order  # type: ignore
    uid = current_user.get("uid")
    amounts = {
        "pro": int(os.getenv("RAZORPAY_PRO_PLAN_AMOUNT", 29900)),
        "creator": int(os.getenv("RAZORPAY_CREATOR_PLAN_AMOUNT", 59900))
    }
    amount = amounts.get(req.plan)
    if not amount:
        raise HTTPException(status_code=400, detail="Invalid plan")
    order = create_order(amount, receipt=f"levi_{req.plan}_{uid}", user_id=uid, plan=req.plan)
    return {"order_id": order["id"], "amount": amount, "currency": "INR", 
            "key": os.getenv("RAZORPAY_KEY_ID")}

@app.post("/verify_payment")
async def confirm_payment(data: PaymentVerify, current_user: dict = Depends(get_current_user)):
    from backend import payments  # type: ignore
    uid = current_user.get("uid")
    valid = payments.verify_razorpay_signature(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    
    # Upgrade user tier in Firestore
    payments.upgrade_user_tier(uid, data.plan or "pro") 
    
    return {"status": "success", "message": f"Payment confirmed and account upgraded to {data.plan}"}

@app.post("/razorpay_webhook")
async def razorpay_webhook(request: Request):
    """
    Handle Razorpay webhooks for payment.captured events in Firestore.
    """
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    # Verify webhook signature
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret or not signature:
        logger.warning("Razorpay webhook missing secret or signature")
        return {"status": "ignored"}

    _secret_str = str(webhook_secret)
    expected_signature = hmac.new(
        _secret_str.encode(), 
        payload, 
        hashlib.sha256
    ).hexdigest()
    
    actual_signature = signature.decode() if isinstance(signature, bytes) else signature
    
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = data.get("event")

    if event == "payment.captured":
        payment_entity = data["payload"]["payment"]["entity"]
        payment_id = payment_entity.get("id")

        if not payment_id:
            return {"status": "error", "message": "Missing payment_id"}

        # Idempotency check: prevent double-crediting using Firestore
        event_ref = firestore_db.collection("payment_events").document(payment_id)
        if event_ref.get().exists:
            logger.info(f"Payment {payment_id} already processed. Skipping.")
            return {"status": "success", "message": "Already processed"}
        
        order_id = payment_entity.get("order_id")
        amount_paise = payment_entity.get("amount", 0)
        amount_inr = amount_paise / 100
        notes = payment_entity.get("notes", {})
        
        user_id = notes.get("user_id")
        plan = notes.get("plan", "pro")
        
        receipt = payment_entity.get("receipt", "")
        if receipt.startswith("levi_"):
            parts = receipt.split("_")
            if len(parts) >= 3:
                plan = parts[1]
                user_id = parts[2]

        if user_id:
            # Create the event in Firestore before upgrading
            event_ref.set({
                "payment_id": payment_id,
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount_inr,
                "status": "captured",
                "created_at": datetime.utcnow()
            })
            
            from backend.payments import upgrade_user_tier
            upgrade_user_tier(user_id, str(plan))
            
            logger.info(f"[PAYMENT_SUCCESS] User: {user_id} | Amount: {amount_inr} INR | Plan: {plan}")

            # Send Receipt Email (assuming user fetch)
            user_doc = firestore_db.collection("users").document(user_id).get()
            if user_doc.exists and user_doc.to_dict().get("email"):
                send_payment_receipt(user_doc.to_dict()["email"], str(plan), amount_inr)
        else:
            logger.warning(f"[PAYMENT_ORPHAN] Received payment but could not identify user. Payment ID: {payment_id}")

    return {"status": "success"}

# Phase 3: Monetization (Razorpay)

@app.get("/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    """
    Get current user's credits and tier from Firestore.
    """
    return {
        "credits": current_user.get("credits"),
        "tier": current_user.get("tier"),
        "share_count": current_user.get("share_count")
    }





@app.post("/downgrade")
async def downgrade_tier(current_user: dict = Depends(get_current_user)):
    """
    Allow users to downgrade to the free tier in Firestore.
    """
    uid = current_user.get("uid")
    if current_user.get("tier") == "free":
        return {"status": "ignored", "message": "Already on free tier"}
    
    firestore_db.collection("users").document(uid).update({"tier": "free"})
    return {"status": "success", "message": "Subscription cancelled. Downgraded to free tier."}



# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# Content Engine API Routes
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

class ContentGenerateRequest(BaseModel):
    content_type: str = Field(..., max_length=50, description="One of: quote, essay, story, script, philosophy, caption, thread, blog, poem, newsletter, readme")
    topic: str = Field(..., max_length=500, description="The subject matter to write about")
    tone: str = Field("inspiring", max_length=50, description="Tone/style of the content")
    depth: str = Field("high", description="Output depth: 'low', 'medium', or 'high'")
    language: str = Field("English", max_length=50, description="Output language (e.g. 'English', 'Spanish', 'Hindi')")

    @validator("topic", "tone")
    def sanitize_content_inputs(cls, v):
        if v:
            v_lower = v.lower()
            for pattern in _INJECTION_PATTERNS:
                if pattern in v_lower:
                    raise ValueError(f"Potential prompt injection detected: {pattern}")
        return v


@app.post("/api/content/generate")
@limiter.limit("20/minute")
async def api_content_generate(
    request: Request,
    body: ContentGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a piece of content using the LEVI content engine.

    Supports 11 content types: quote, essay, story, script, philosophy,
    caption, thread, blog, poem, newsletter, readme.

    Rate-limited to 20 requests per minute per user. Requires authentication.
    """
    try:
        try:
            from backend.content_engine import generate_content  # type: ignore
        except ImportError:
            from content_engine import generate_content  # type: ignore

        result = generate_content(
            content_type=body.content_type,
            topic=body.topic,
            tone=body.tone,
            depth=body.depth,
            language=body.language,
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ContentEngine] Generation failed: {e}")
        raise HTTPException(status_code=500, detail="Content generation failed. Please try again.")


@app.get("/api/content/types")
async def api_content_types():
    """Return all supported content types."""
    try:
        try:
            from backend.content_engine import get_available_types  # type: ignore
        except ImportError:
            from content_engine import get_available_types  # type: ignore
        return {"types": get_available_types()}
    except Exception as e:
        logger.error(f"[ContentEngine] Failed to fetch types: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve content types.")


@app.get("/api/content/tones")
async def api_content_tones():
    """Return all supported content tones."""
    try:
        try:
            from backend.content_engine import get_available_tones  # type: ignore
        except ImportError:
            from content_engine import get_available_tones  # type: ignore
        return {"tones": get_available_tones()}
    except Exception as e:
        logger.error(f"[ContentEngine] Failed to fetch tones: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve content tones.")


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# Image Engine API Routes
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u@app.post("/api/personas")
async def api_create_persona(
    body: PersonaCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new AI Persona system template in Firestore.
    """
    try:
        uid = current_user.get("uid")
        persona_data = {
            "user_id": uid,
            "name": body.name,
            "description": body.description,
            "system_prompt": body.system_prompt,
            "avatar_url": body.avatar_url,
            "is_public": body.is_public,
            "created_at": datetime.utcnow()
        }
        
        update_time, doc_ref = firestore_db.collection("personas").add(persona_data)
        persona_data["id"] = doc_ref.id
        
        return {"status": "success", "message": "Persona created in Firestore", "persona": persona_data}
    except Exception as e:
        logger.error(f"[Personas] Failed to create persona in Firestore: {e}")
        raise HTTPException(status_code=500, detail="Could not create AI persona.")
─────────────────────────────────

@app.get("/api/personas")
async def api_get_personas():
    """
    List all available AI Personas from Firestore.
    """
    try:
        personas_ref = firestore_db.collection("personas")
        docs = personas_ref.where("is_public", "==", True).get()
        
        results = []
        for doc in docs:
            p = doc.to_dict()
            p["id"] = doc.id
            results.append(p)
            
        return {"personas": results}
    except Exception as e:
        logger.error(f"[Personas] Failed to fetch personas from Firestore: {e}")
        return {"personas": []}


@app.post("/api/personas")
async def api_create_persona(
    body: PersonaCreate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new AI Persona system template for personalized generation.
    """
    try:
        try:
             from backend.models import Persona  # type: ignore
        except ImportError:
             from models import Persona  # type: ignore

        new_persona = Persona(
            user_id=current_user.id,
            name=body.name,
            description=body.description,
            system_prompt=body.system_prompt,
            avatar_url=body.avatar_url,
            is_public=body.is_public
        )
        db.add(new_persona)
        db.commit()
        db.refresh(new_persona)
        return {"status": "success", "message": "Persona created", "persona": new_persona}
    except Exception as e:
        logger.error(f"[Personas] Failed to create persona: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not create AI persona.")

# ──────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)



