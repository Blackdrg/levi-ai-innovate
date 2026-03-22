
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from sqlalchemy.orm import Session

from pydantic import BaseModel, Field, validator

from jose import JWTError, jwt # type: ignore

from passlib.context import CryptContext # type: ignore

from datetime import datetime, timedelta, date

from slowapi import Limiter

from slowapi.util import get_remote_address

from slowapi.errors import RateLimitExceeded

from slowapi import _rate_limit_exceeded_handler
from authlib.integrations.starlette_client import OAuth # type: ignore
import os
import sentry_sdk

import logging
import json
from pythonjsonlogger.json import JsonFormatter
import time
import uuid

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
formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
logger.propagate = False # Prevent double logging

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
        send_default_pii=False, # Optional: include user data
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
    is_prod = os.getenv("RENDER") or os.getenv("DIGITALOCEAN") or os.getenv("ENVIRONMENT") == "production"
    
    if missing:
        error_msg = f"CRITICAL: Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        if is_prod:
             raise RuntimeError(error_msg)
        else:
             print(f"\n⚠️  WARNING: {error_msg}\n")

validate_env()
# ─────────────────────────────────────────────────────────────

try:
    from backend.db import SessionLocal, engine, get_db, DATABASE_URL
    from backend.models import Quote, Analytics, FeedItem, Base, Users, UserMemory, ChatHistory, PushSubscription
    from backend.embeddings import embed_text, cosine_sim, HAS_MODEL
    from backend.redis_client import (
        get_cached_search, cache_search, get_conversation, save_conversation, 
        HAS_REDIS, REDIS_URL, cache_quote_embedding, get_cached_embedding
    )
    from backend.generation import generate_quote, generate_response
    from backend.image_gen import generate_quote_image
    from backend.video_gen import generate_quote_video
    from backend.email_service import send_daily_quote, send_payment_receipt
    from backend.payments import router as payments_router, use_credits, verify_payment_signature, verify_razorpay_signature, upgrade_user_tier
    from backend.tasks import generate_video_task as generate_video_async
    from backend.learning import (
        collect_training_sample, UserPreferenceModel,
        AdaptivePromptManager, get_learning_stats, infer_implicit_feedback
    )
    from backend.trainer import trigger_training_pipeline, get_model_history, get_active_model_id, generate_with_active_model
    from backend.training_models import TrainingData, ResponseFeedback, ModelVersion, TrainingJob
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Could not import from backend.*: {e}. Falling back to local imports.")
    try:
        from db import SessionLocal, engine, get_db, DATABASE_URL
        from models import Quote, Analytics, FeedItem, Base, Users, UserMemory, ChatHistory, PushSubscription
        from embeddings import embed_text, cosine_sim, HAS_MODEL
        from redis_client import (
            get_cached_search, cache_search, get_conversation, save_conversation, 
            HAS_REDIS, REDIS_URL, cache_quote_embedding, get_cached_embedding
        )
        from generation import generate_quote, generate_response
        from image_gen import generate_quote_image
        from video_gen import generate_quote_video
        from email_service import send_daily_quote, send_payment_receipt
        from payments import router as payments_router, use_credits, verify_payment_signature, verify_razorpay_signature, upgrade_user_tier
        from tasks import generate_video_task as generate_video_async
        from learning import (
            collect_training_sample, UserPreferenceModel,
            AdaptivePromptManager, get_learning_stats, infer_implicit_feedback
        )
        from trainer import trigger_training_pipeline, get_model_history, get_active_model_id, generate_with_active_model
        from training_models import TrainingData, ResponseFeedback, ModelVersion, TrainingJob
    except (ImportError, ModuleNotFoundError) as e2:
        logger.error(f"Fallback imports also failed: {e2}")
        raise e2

import numpy as np
import hashlib
import base64
from io import BytesIO
from typing import List, Optional
from sqlalchemy import func
import asyncio
import hmac
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)

SECRET_KEY = os.environ["SECRET_KEY"]
CLIENT_KEY = os.getenv("CLIENT_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days for better user experience

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

import uuid

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    
    # Store JTI in Redis (whitelist)
    from backend.redis_client import store_jti
    # Convert timedelta to seconds for Redis EX
    delta = expires_delta or timedelta(minutes=15)
    seconds = int(delta.total_seconds())
    store_jti(jti, seconds)
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) # type: ignore

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        jti = payload.get("jti")
        if not jti:
             raise credentials_exception
        
        # Check JTI in Redis (whitelist)
        from backend.redis_client import is_jti_blacklisted
        if is_jti_blacklisted(jti):
             raise credentials_exception
             
    except JWTError:
        raise credentials_exception
    username_val = payload.get("sub")
    if username_val is None:
        raise credentials_exception
    username: str = str(username_val)
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_optional(token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="token", auto_error=False)), db: Session = Depends(get_db)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        jti = payload.get("jti")
        if not jti:
            return None
            
        from backend.redis_client import is_jti_blacklisted
        if is_jti_blacklisted(jti):
            return None
            
        username_val = payload.get("sub")
        if username_val is None:
            return None
        username: str = str(username_val)
        return db.query(Users).filter(Users.username == username).first()
    except JWTError:
        return None

async def verify_admin(request: Request):
    admin_key = os.getenv("ADMIN_KEY")
    provided_key = request.headers.get("X-Admin-Key")
    if not admin_key or provided_key != admin_key:
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

class Token(BaseModel):
    access_token: str
    token_type: str

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
        # Basic prompt injection detection
        forbidden = ["ignore previous", "system:", "assistant:", "user:"]
        v_lower = v.lower()
        for f in forbidden:
            if f in v_lower:
                raise ValueError(f"Potential prompt injection detected: {f}")
        return v

class ChatMessage(BaseModel):
    session_id: str = Field(..., max_length=100)
    message: str = Field(..., max_length=1000)
    lang: Optional[str] = Field("en", max_length=10)
    mood: Optional[str] = Field("", max_length=50)

    @validator("message")
    def sanitize_message(cls, v):
        forbidden = ["ignore previous", "system:", "assistant:", "user:"]
        v_lower = v.lower()
        for f in forbidden:
            if f in v_lower:
                raise ValueError(f"Potential prompt injection detected: {f}")
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

is_prod = os.getenv("RENDER") or os.getenv("DIGITALOCEAN") or os.getenv("ENVIRONMENT") == "production"

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
        "duration_ms": round(duration, 2)
    })
    
    return response

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.include_router(payments_router)

# Rate Limiter setup
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from typing import Any, cast
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

# Ensure database tables are created
Base.metadata.create_all(bind=engine)



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
]

for o in env_origins:
    origin = o.strip()
    if origin and origin != "*" and origin not in origins:
        origins.append(origin)

allow_all = os.getenv("CORS_ORIGINS", "").strip() == "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Essential Session Middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# OAuth Configuration
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@app.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for('auth_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")
        
        email = user_info.get('email')
        username = email.split('@')[0] # Simple username generation
        
        # Check if user exists, if not create them
        user = db.query(Users).filter(Users.username == username).first()
        if not user:
            user = Users(
                username=username,
                email=email,
                password_hash=get_password_hash(os.urandom(16).hex()), # Random password for OAuth users
                is_verified=1 # OAuth users are verified by Google
            )
            db.add(user)
            db.commit()
        elif not user.is_verified:
            # If user exists but wasn't verified, Google login verifies them
            user.is_verified = 1
            db.commit()
            
        # Generate JWT token
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        # Redirect to frontend with token (adjust URL as needed for your frontend)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
        return RedirectResponse(url=f"{frontend_url}?token={access_token}")
        
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

@app.exception_handler(Exception)

async def global_exception_handler(request: Request, exc: Exception):

    import traceback

    logger.error(f"Unhandled error on {request.url}: {exc}\n{traceback.format_exc()}")

    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})





@app.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Logout by revoking the current JWT's JTI.
    """
    try:
        # Decode without verification to get JTI if possible, 
        # but better to use verified payload if we have it.
        # Since Depends(oauth2_scheme) gives us the token, we decode it.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        jti = payload.get("jti")
        if jti:
            from backend.redis_client import delete_jti
            delete_jti(jti)
        return {"status": "success", "message": "Logged out successfully"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting LEVI backend...")

    if not HAS_REDIS:

        logger.warning("Redis unavailable — using in-memory fallback.")

    else:

        masked = REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL

        logger.info(f"Redis connected: {masked}")

    try:

        Base.metadata.create_all(bind=engine)

        logger.info("Database tables ready.")

    except Exception as e:

        logger.error(f"Error creating tables: {e}")

    logger.info(f"DB scheme: {DATABASE_URL.split('://')[0] if DATABASE_URL else 'None'}")

    logger.info(f"CLIENT_KEY: {'SET' if CLIENT_KEY else 'NOT SET'}")





@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"status": "ok", "message": "LEVI backend is running", "docs": "/docs", "health": "/health"}





@app.get("/health")

def health():

    return {

        "status": "ok",

        "version": "2.1.0",

        "search_mode": "semantic" if HAS_MODEL else "random_fallback",

        "redis": HAS_REDIS,

    }





@app.get("/daily_quote")

def daily_quote(db: Session = Depends(get_db)):

    try:

        from backend.generation import fetch_open_source_quote

    except ImportError:

        from generation import fetch_open_source_quote

    os_quote = fetch_open_source_quote()

    if os_quote:

        return {"quote": os_quote['quote'], "author": os_quote['author']}

    today_quote = db.query(Quote).order_by(func.random()).first()

    if not today_quote:

        return {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"}

    return {"quote": today_quote.text, "author": today_quote.author}





@app.get("/analytics")

def get_analytics(db: Session = Depends(get_db)):

    total_chats = db.query(func.sum(Analytics.chats_count)).scalar() or 0

    popular_topics = (

        db.query(Quote.topic, func.count(Quote.id))

        .group_by(Quote.topic).order_by(func.count(Quote.id).desc()).limit(5).all()

    )

    return {

        "total_chats": total_chats,

        "daily_users": 0,

        "popular_topics": [t for t, _ in popular_topics if t],

        "likes_count": 0,

    }





@app.post("/search_quotes", response_model=List[dict])

def search_quotes(query: Query, db: Session = Depends(get_db)):

    query_hash = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()

    cached = get_cached_search(query_hash)

    if cached:

        return cached

    if not query.text:
        results = db.query(Quote).order_by(func.random()).limit(query.top_k).all()
    elif not HAS_MODEL:
        # Keyword fallback for Render free tier
        base_q = db.query(Quote)
        if query.mood:
            base_q = base_q.filter(Quote.mood == query.mood)
        results = base_q.filter(Quote.text.ilike(f"%{query.text}%")).limit(query.top_k).all()
        # If no keyword matches, fallback to random
        if not results:
            results = base_q.order_by(func.random()).limit(query.top_k).all()
    else:
        query_embedding = embed_text(query.text)

        if "postgresql" in DATABASE_URL:

            base_q = db.query(Quote)

            if query.mood:

                base_q = base_q.filter(Quote.mood == query.mood)

            results = base_q.order_by(Quote.embedding.l2_distance(query_embedding)).limit(query.top_k).all()

        else:
            all_q = db.query(Quote)
            if query.mood:
                all_q = all_q.filter(Quote.mood == query.mood)
            all_quotes = all_q.all()
            q_emb = np.array(query_embedding)
            
            scored = []
            for q in all_quotes:
                cached_emb = get_cached_embedding(q.id)
                if cached_emb:
                    emb = np.array(cached_emb)
                elif q.embedding is not None:
                    emb = np.array(q.embedding)
                    cache_quote_embedding(q.id, q.embedding)
                else:
                    continue
                scored.append((q, cosine_sim(q_emb, emb)))

            scored.sort(key=lambda x: x[1], reverse=True)
            results = [s[0] for s in scored[:query.top_k]]

    formatted = [
        {"quote": q.text, "author": q.author, "topic": q.topic, "mood": q.mood,
         "similarity": 1.0 if not HAS_MODEL and query.text and query.text.lower() in q.text.lower() else 0.9,
         "search_mode": "semantic" if HAS_MODEL else ("keyword" if query.text and results else "random_fallback")}
        for q in results
    ]

    cache_search(query_hash, formatted)

    return formatted





@app.post("/generate")

def gen_quote(prompt: Query):

    generated = generate_quote(prompt.text, mood=prompt.mood or "")

    return {"generated_quote": generated}





@app.post("/generate_image")
@limiter.limit("5/minute")
async def gen_image(request: Request, req: Query, db: Session = Depends(get_db), current_user: Optional[Users] = Depends(get_current_user_optional)):
    try:
        user_id = current_user.id if current_user else None
        user_tier = current_user.tier if current_user else "free"
        
        # Security: Validate custom_bg if provided
        if req.custom_bg:
            # Check size (approximate for base64)
            if len(req.custom_bg) > 7 * 1024 * 1024: # ~5MB after decoding
                raise HTTPException(status_code=400, detail="Custom background exceeds 5MB limit")
            
            # Basic type check
            allowed_types = ["data:image/jpeg", "data:image/png", "data:image/webp"]
            if not any(req.custom_bg.startswith(t) for t in allowed_types):
                raise HTTPException(status_code=400, detail="Invalid image format. Only JPEG, PNG and WEBP are allowed.")
        
        # Credit System: Deduct 1 credit for generation
        if current_user:
            use_credits(current_user.id, amount=1, db=db)
            
        # Check if we should use Celery for async processing (Scale Infrastructure)
        # Default to True in production (Render/DigitalOcean)
        USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"
        
        if USE_CELERY:
            from backend.tasks import generate_image_task
            task = generate_image_task.delay(
                req.text, 
                req.author or "Unknown",
                req.mood or "neutral",
                user_id
            )
            return {"task_id": task.id, "status": "processing", "message": "Image generation started in background."}

        loop = asyncio.get_event_loop()
        bio = await loop.run_in_executor(
            _executor,
            lambda: generate_quote_image(
                req.text, 
                author=req.author or "Unknown",
                mood=req.mood or "neutral", 
                custom_bg=req.custom_bg or "",
                user_tier=user_tier
            ),
        )

        img_b64 = base64.b64encode(bio.getvalue()).decode()

        img_data = f"data:image/png;base64,{img_b64}"

        new_feed = FeedItem(
            user_id=user_id,
            text=req.text, 
            author=req.author or "Unknown",
            mood=req.mood or "neutral", 
            image_b64=img_data, 
            likes=0
        )

        db.add(new_feed)

        db.commit()

        db.refresh(new_feed)

        return {"id": new_feed.id, "image_b64": img_data}

    except Exception as e:

        import traceback

        logger.error(f"Image generation error: {e}\n{traceback.format_exc()}")

        raise HTTPException(status_code=500, detail=str(e))





@app.post("/like/{item_type}/{item_id}")

def like_item(item_type: str, item_id: int, db: Session = Depends(get_db)):

    if item_type == "quote":

        item = db.query(Quote).filter(Quote.id == item_id).first()

    elif item_type == "feed":

        item = db.query(FeedItem).filter(FeedItem.id == item_id).first()

    else:

        raise HTTPException(status_code=400, detail="Invalid item type")

    if not item:

        raise HTTPException(status_code=404, detail="Item not found")

    item.likes = (item.likes or 0) + 1

    today = date.today()

    analytics = db.query(Analytics).filter(Analytics.date == today).first()

    if analytics:

        analytics.likes_count = (analytics.likes_count or 0) + 1

    db.commit()

    return {"status": "success", "new_likes": item.likes}





@app.get("/feed", response_model=List[dict])
def get_feed(db: Session = Depends(get_db), limit: int = 20, offset: int = 0):
    items = db.query(FeedItem).order_by(FeedItem.timestamp.desc()).offset(offset).limit(limit).all()
    return [{"id": i.id, "text": i.text, "author": i.author, "mood": i.mood,
            "image": i.image_url or i.image_b64, "likes": i.likes or 0, "time": i.timestamp.isoformat()}
            for i in items]





@app.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    msg: ChatMessage,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    user_id = current_user.id if current_user else None
    logger.info(f"Chat [{msg.session_id}] (User: {user_id}): '{msg.message[:60]}'")

    # Analytics
    today = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if not analytics:
        analytics = Analytics(date=today, chats_count=1)
        db.add(analytics)
    else:
        analytics.chats_count = (analytics.chats_count or 0) + 1

    # User memory
    user_mem = None
    if user_id:
        user_mem = db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        if not user_mem:
            user_mem = UserMemory(user_id=user_id, mood_history=[], liked_topics=[], interaction_count=0)
            db.add(user_mem)
        user_mem.interaction_count += 1

    db.commit()

    # Load history
    history = get_conversation(msg.session_id)

    # Infer implicit feedback from previous turn
    try:
        from learning import infer_implicit_feedback, collect_training_sample
        implicit_rating = infer_implicit_feedback(history, msg.message)
        if implicit_rating and len(history) >= 1:
            prev = history[-1]
            collect_training_sample(
                db=db,
                user_message=prev.get("user", ""),
                bot_response=prev.get("bot", ""),
                mood=msg.mood or "philosophical",
                rating=implicit_rating,
                session_id=msg.session_id,
                user_id=user_id,
            )
    except Exception as e:
        logger.warning(f"Implicit feedback collection failed: {e}")

    # Build personalised system prompt for authenticated users
    personalized_system = None
    try:
        if user_id:
            from learning import UserPreferenceModel, AdaptivePromptManager
            pref = UserPreferenceModel(db, user_id)
            base = AdaptivePromptManager(db).get_best_variant(msg.mood or "philosophical")
            personalized_system = pref.build_system_prompt(base, msg.mood or "philosophical")
    except Exception:
        pass  # graceful degradation

    # Use fine-tuned model if available
    try:
        from trainer import generate_with_active_model
        if generate_with_active_model.__module__:  # check it imported
            bot_response = generate_with_active_model(
                prompt=msg.message,
                system_prompt=personalized_system or "You are LEVI, a philosophical AI muse.",
                max_tokens=150,
            )
            if not bot_response:
                raise ValueError("Empty response from active model")
    except Exception:
        # Fall back to standard generation
        bot_response = generate_response(
            msg.message,
            history=history,
            mood=msg.mood or "",
            lang=msg.lang or "en",
            user_memory=user_mem,
        )

    # Store this turn as training data (auto-scored)
    try:
        from learning import collect_training_sample
        collect_training_sample(
            db=db,
            user_message=msg.message,
            bot_response=bot_response,
            mood=msg.mood or "philosophical",
            rating=None,         # will be auto-scored or updated via /feedback
            session_id=msg.session_id,
            user_id=user_id,
        )
    except Exception as e:
        logger.warning(f"Training data collection failed: {e}")

    # Save conversation history
    history.append({"user": msg.message, "bot": bot_response})
    save_conversation(msg.session_id, history)

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
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional),
):
    """
    User rates a response 1-5.
    Immediately stores the conversation as training data with the given rating.
    High-rated responses are added to the knowledge base in real-time.
    """
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    user_id = current_user.id if current_user else None

    try:
        from learning import collect_training_sample
        from training_models import ResponseFeedback

        # Store training sample
        sample = collect_training_sample(
            db=db,
            user_message=req.user_message,
            bot_response=req.bot_response,
            mood=req.mood or "philosophical",
            rating=req.rating,
            session_id=req.session_id,
            user_id=user_id,
        )

        # Store explicit feedback record
        fb = ResponseFeedback(
            training_data_id=sample.id,
            user_id=user_id,
            session_id=req.session_id,
            message_hash=req.message_hash,
            rating=req.rating,
            feedback_type=req.feedback_type,
        )
        db.add(fb)
        db.commit()

        return {"status": "success", "sample_id": sample.id, "rating": req.rating}

    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")


# ── Learning: Get personalised system prompt preview ─────────────────────────
@app.get("/learning/my_profile")
async def get_my_learning_profile(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Returns the AI's current learned profile for this user."""
    from learning import UserPreferenceModel
    model = UserPreferenceModel(db, current_user.id)
    profile = model.get_profile()
    return {
        "user_id": current_user.id,
        "profile": profile,
        "system_prompt_preview": model.build_system_prompt(
            "You are LEVI, a philosophical AI.", "philosophical"
        )[:200] + "...",
    }


# ── Learning: Admin stats ─────────────────────────────────────────────────────
@app.get("/learning/stats")
async def get_learning_stats_route(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Returns learning system statistics. Admin-level endpoint."""
    from learning import get_learning_stats
    stats = get_learning_stats(db)
    return stats


# ── Training: Model history ───────────────────────────────────────────────────
@app.get("/model/versions")
async def get_model_versions(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Returns all fine-tuned model versions."""
    from trainer import get_model_history, get_active_model_id
    versions = get_model_history(db)
    return {
        "active_model": get_active_model_id() or "groq/llama3-8b-8192 (base)",
        "versions": versions,
    }


# ── Training: Manually trigger a training run (admin only) ───────────────────
@app.post("/model/trigger_training")
async def trigger_training_manually(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Manually trigger a fine-tuning run. Admin use only."""
    # Basic admin check: only creator-tier users can trigger training
    if current_user.tier not in ("creator", "admin"):
        raise HTTPException(status_code=403, detail="Requires creator tier")

    from trainer import trigger_training_pipeline
    task = trigger_training_pipeline.delay()
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Training pipeline queued. Check /task_status/{task_id} for progress.",
    }


# ── Training: Current model status ───────────────────────────────────────────
@app.get("/model/status")
async def model_status(db: Session = Depends(get_db)):
    """Public endpoint: returns which model is powering LEVI right now."""
    from trainer import get_active_model_id
    from training_models import TrainingJob
    from learning import get_learning_stats

    active = get_active_model_id()
    stats  = get_learning_stats(db)

    # Latest training job
    latest_job = db.query(TrainingJob).order_by(TrainingJob.created_at.desc()).first()

    return {
        "active_model": active or "groq/llama3-8b-8192",
        "is_fine_tuned": active is not None,
        "training_samples_collected": stats["total_training_samples"],
        "knowledge_base_entries":     stats["learned_quotes"],
        "latest_training_job": {
            "status": latest_job.status if latest_job else "none",
            "created_at": latest_job.created_at.isoformat() if latest_job else None,
        } if latest_job else None,
    }
@app.get("/export_my_data")
async def export_my_data(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """
    GDPR Compliance: Export all data associated with the current user.
    """
    try:
        # Fetch user profile
        profile = {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "tier": current_user.tier,
            "credits": current_user.credits,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None
        }
        
        # Fetch chat history
        chats = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).all()
        chat_data = [
            {"message": c.message, "response": c.response, "timestamp": c.timestamp.isoformat()}
            for c in chats
        ]
        
        # Fetch feed items (generations)
        items = db.query(FeedItem).filter(FeedItem.user_id == current_user.id).all()
        item_data = [
            {
                "text": i.text,
                "author": i.author,
                "mood": i.mood,
                "image_url": i.image_url,
                "video_url": i.video_url,
                "timestamp": i.timestamp.isoformat()
            }
            for i in items
        ]
        
        export = {
            "profile": profile,
            "chats": chat_data,
            "generations": item_data,
            "exported_at": datetime.utcnow().isoformat()
        }
        
        return export
    except Exception as e:
        logger.error(f"Data export failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data.")

@app.delete("/delete_account")
async def delete_account(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """
    GDPR/Legal Compliance: Delete user account and all associated data.
    """
    try:
        # Delete related records first (cascade should handle some but being explicit is safer)
        db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).delete()
        db.query(UserMemory).filter(UserMemory.user_id == current_user.id).delete()
        
        # Keep FeedItems but anonymize them (or delete them if preferred)
        # For now, we'll keep the art but remove the link to the user
        db.query(FeedItem).filter(FeedItem.user_id == current_user.id).update({"user_id": None})
        
        # Finally delete the user
        db.delete(current_user)
        db.commit()
        
        logger.info(f"Account deleted for user: {current_user.username}")
        return {"status": "success", "message": "Account and all personal data deleted."}
    except Exception as e:
        db.rollback()
        logger.error(f"Account deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account.")

@app.get("/profile")
async def get_profile(current_user: Users = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "tier": current_user.tier,
        "credits": current_user.credits,
        "share_count": current_user.share_count or 0,
        "bonus_credits": current_user.bonus_credits or 0,
        "created_at": current_user.created_at.isoformat()
    }

@app.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserIn, db: Session = Depends(get_db)):
    if len(user_in.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Check if username looks like an email
    if "@" not in user_in.username or "." not in user_in.username:
         raise HTTPException(status_code=400, detail="Username must be a valid email address")

    existing = db.query(Users).filter(Users.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate verification token
    verification_token = str(uuid.uuid4())
    
    user = Users(
        username=user_in.username,
        email=user_in.username,
        password_hash=get_password_hash(user_in.password),
        is_verified=0,
        verification_token=verification_token
    )
    db.add(user)
    db.commit()
    
    # Send verification email
    from backend.email_service import send_verification_email
    send_verification_email(user.username, verification_token)
    
    return JSONResponse(
        status_code=201,
        content={"message": "Registration successful. Please check your email to verify your account."}
    )

@app.get("/verify")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    user.is_verified = 1
    user.verification_token = None
    db.commit()
    
    # Redirect to login or success page
    frontend_url = os.getenv("FRONTEND_URL", "https://levi-ai.create.app")
    return RedirectResponse(url=f"{frontend_url}/auth.html?verified=true")

@app.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email address before logging in.")
    
    token = create_access_token(data={"sub": user.username},
                                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}

@app.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login_json(request: Request, user_in: UserIn, db: Session = Depends(get_db)):
    """
    Alternative login route that accepts JSON body instead of form-data.
    Fixes 404/compatibility issues in some production environments.
    """
    user = db.query(Users).filter(Users.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email address before logging in.")
        
    token = create_access_token(data={"sub": user.username},
                                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}

# Phase 2: Viral Loops & Engagement

@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check the status of a Celery background task.
    """
    from backend.tasks import celery_app
    from celery.result import AsyncResult
    
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
async def track_share(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """
    Track when a user shares content. Reward them after 5 shares.
    """
    current_user.share_count = (current_user.share_count or 0) + 1
    rewarded = False
    if current_user.share_count % 5 == 0:
        current_user.bonus_credits = (current_user.bonus_credits or 0) + 10
        rewarded = True
    db.commit()
    return {
        "status": "success", 
        "share_count": current_user.share_count, 
        "rewarded": rewarded,
        "bonus_credits": current_user.bonus_credits
    }

@app.post("/generate_video")
async def gen_video(req: Query, db: Session = Depends(get_db), current_user: Optional[Users] = Depends(get_current_user)):
    try:
        user_id = current_user.id if current_user else None
        
        # Default to True in production
        USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"
        
        if USE_CELERY:
            from backend.tasks import generate_video_task
            task = generate_video_task.delay(
                req.text, 
                req.author or "Unknown",
                req.mood or "neutral",
                user_id
            )
            return {"task_id": task.id, "status": "processing", "message": "Video generation started in background."}

        from backend.video_gen import generate_quote_video
        video_bytes = generate_quote_video(
            req.text, 
            author=req.author or "Unknown",
            mood=req.mood or "neutral"
        )
        
        # Persistence for sync video (if used)
        new_item = FeedItem(
            user_id=user_id,
            text=req.text,
            author=req.author or "Unknown",
            mood=req.mood or "neutral",
            # We don't have an easy way to store raw video bytes in DB, 
            # so sync video without S3 is less persistent than async.
        )
        db.add(new_item)
        db.commit()

        return Response(content=video_bytes, media_type="video/mp4")
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/my_gallery")
async def get_my_gallery(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user), limit: int = 20, offset: int = 0):
    """Fetch all generated items for the current user."""
    items = db.query(FeedItem).filter(FeedItem.user_id == current_user.id).order_by(FeedItem.timestamp.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": i.id,
            "text": i.text,
            "author": i.author,
            "mood": i.mood,
            "image": getattr(i, 'image_url', None) or i.image_b64,
            "video": getattr(i, 'video_url', None),
            "likes": i.likes or 0,
            "time": i.timestamp.isoformat()
        }
        for i in items
    ]

# ─────────────────────────────────────────────────────────────
# Admin Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/admin/users")
async def admin_list_users(db: Session = Depends(get_db), _admin: bool = Depends(verify_admin)):
    users = db.query(Users).order_by(Users.created_at.desc()).all()
    return [{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "tier": u.tier,
        "credits": u.credits,
        "is_verified": u.is_verified,
        "created_at": u.created_at.isoformat() if u.created_at else None
    } for u in users]

@app.get("/admin/feed")
async def admin_list_feed(db: Session = Depends(get_db), limit: int = 50, offset: int = 0, _admin: bool = Depends(verify_admin)):
    items = db.query(FeedItem).order_by(FeedItem.timestamp.desc()).offset(offset).limit(limit).all()
    return [{
        "id": i.id,
        "user_id": i.user_id,
        "text": i.text,
        "author": i.author,
        "mood": i.mood,
        "image_url": i.image_url,
        "video_url": i.video_url,
        "likes": i.likes,
        "timestamp": i.timestamp.isoformat()
    } for i in items]

@app.delete("/admin/feed/{item_id}")
async def admin_delete_feed_item(item_id: int, db: Session = Depends(get_db), _admin: bool = Depends(verify_admin)):
    item = db.query(FeedItem).filter(FeedItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"status": "success", "message": f"Item {item_id} deleted"}

@app.post("/admin/adjust_credits")
async def admin_adjust_credits(adj: AdminAdjustCredits, db: Session = Depends(get_db), _admin: bool = Depends(verify_admin)):
    user = db.query(Users).filter(Users.id == adj.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.credits = (user.credits or 0) + adj.amount
    db.commit()
    return {"status": "success", "new_credits": user.credits}

@app.get("/admin/payments")
async def admin_list_payments(_admin: bool = Depends(verify_admin)):
    """
    In a real app, you might query a Payments table. 
    For now, we can check recent success logs or Redis idempotency keys.
    """
    # For now, return a placeholder or implement if a Payments table existed.
    return {"message": "Payment history can be viewed in Razorpay Dashboard for now."}

# ─────────────────────────────────────────────────────────────

@app.post("/test_daily_email")
async def test_daily_email(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """
    Test sending a daily wisdom email to the current user.
    """
    user_mem = db.query(UserMemory).filter(UserMemory.user_id == current_user.id).first()
    topics = user_mem.liked_topics if user_mem else ["wisdom"]
    mood = user_mem.mood_history[-1] if user_mem and user_mem.mood_history else "philosophical"
    
    success = send_daily_quote(
        user_email=current_user.username, # Assuming username is an email for now
        user_name=current_user.username.split('@')[0],
        liked_topics=topics,
        last_mood=mood
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email. Check API key.")
    
    return {"status": "success", "message": "Daily wisdom email sent!"}

@app.get("/users/me")
async def get_me(current_user: Users = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "tier": current_user.tier,
        "credits": current_user.credits,
        "share_count": current_user.share_count,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
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
async def subscribe_push(sub: PushSubscriptionSchema, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    # Check if subscription already exists for this endpoint
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == sub.endpoint).first()
    
    p256dh = str(sub.keys.get("p256dh", ""))
    auth = str(sub.keys.get("auth", ""))
    
    if not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Invalid push subscription keys")

    if existing:
        existing.user_id = current_user.id
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        new_sub = PushSubscription(
            user_id=current_user.id,
            endpoint=sub.endpoint,
            p256dh=p256dh,
            auth=auth
        )
        db.add(new_sub)
    
    db.commit()
    return {"status": "success", "message": "Subscribed to push notifications"}

@app.post("/push/send_test")
async def send_test_push(current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.tasks import send_push_notification_task
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == current_user.id).all()
    if not subs:
        raise HTTPException(status_code=404, detail="No push subscriptions found for this user")
    
    for s in subs:
        send_push_notification_task.delay(
            s.id,
            s.endpoint,
            s.p256dh,
            s.auth,
            "LEVI Wisdom",
            "This is a test notification from your daily wisdom guide. ✨"
        )
    return {"status": "success", "message": f"Sent {len(subs)} test notifications"}

@app.post("/create_order")
def new_order(req: OrderRequest, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    from backend.payments import create_order
    amounts = {
        "pro": int(os.getenv("RAZORPAY_PRO_PLAN_AMOUNT", 29900)),
        "creator": int(os.getenv("RAZORPAY_CREATOR_PLAN_AMOUNT", 59900))
    }
    amount = amounts.get(req.plan)
    if not amount:
        raise HTTPException(status_code=400, detail="Invalid plan")
    order = create_order(amount, receipt=f"levi_{req.plan}_{current_user.id}", user_id=current_user.id, plan=req.plan)
    return {"order_id": order["id"], "amount": amount, "currency": "INR", 
            "key": os.getenv("RAZORPAY_KEY_ID")}

@app.post("/verify_payment")
def confirm_payment(data: PaymentVerify, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    from backend import payments
    valid = payments.verify_razorpay_signature(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    
    # Upgrade user tier in DB
    payments.upgrade_user_tier(current_user.id, data.plan or "pro", db) 
    
    return {"status": "success", "message": f"Payment confirmed and account upgraded to {data.plan}"}

@app.post("/razorpay_webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Razorpay webhooks for payment.captured events.
    """
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    # Verify webhook signature
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret or not signature:
        logger.warning("Razorpay webhook missing secret or signature")
        return {"status": "ignored"}

    expected_signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    
    # Ensure signature is a string for comparison
    actual_signature = signature.decode() if isinstance(signature, bytes) else signature
    
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.error("Failed to parse Razorpay webhook payload as JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = data.get("event")

    if event == "payment.captured":
        payment_entity = data["payload"]["payment"]["entity"]
        payment_id = payment_entity.get("id")

        if not payment_id:
            logger.error("Razorpay webhook missing payment_id")
            return {"status": "error", "message": "Missing payment_id"}

        # Idempotency check: prevent double-crediting
        from backend.redis_client import _get, _set, HAS_REDIS
        processed_key = f"payment_processed:{payment_id}"
        if _get(processed_key):
            logger.info(f"Payment {payment_id} already processed. Skipping.")
            return {"status": "success", "message": "Already processed"}
        
        # Mark as processed in Redis (24h TTL)
        _set(processed_key, "1", ex=86400)

        order_id = payment_entity.get("order_id")
        amount = payment_entity.get("amount", 0) / 100 # Convert paise to INR
        notes = payment_entity.get("notes", {})
        
        # Security: Re-derive user and plan from notes/receipt (verified by signature)
        user_id = notes.get("user_id")
        plan = notes.get("plan", "pro")
        
        receipt = payment_entity.get("receipt", "")
        if receipt.startswith("levi_"):
            parts = receipt.split("_")
            if len(parts) >= 3:
                plan = parts[1]
                user_id = parts[2]

        if user_id:
            from backend.payments import upgrade_user_tier
            upgrade_user_tier(int(user_id), str(plan), db)
            
            # Audit Trail: Log payment success
            logger.info(f"[PAYMENT_SUCCESS] User: {user_id} | Amount: {amount} INR | Plan: {plan} | Order: {order_id} | Payment: {payment_id}")

            # Send Receipt Email
            user = db.query(Users).filter(Users.id == int(user_id)).first()
            if user and user.email:
                send_payment_receipt(user.email, str(plan), amount)
        else:
            logger.warning(f"[PAYMENT_ORPHAN] Received payment but could not identify user. Payment ID: {payment_id}")

    return {"status": "success"}

# Phase 3: Monetization (Razorpay)

@app.get("/credits")
async def get_user_credits(current_user: Users = Depends(get_current_user)):
    """
    Get current user's credits and tier.
    """
    return {
        "credits": current_user.credits,
        "tier": current_user.tier,
        "share_count": current_user.share_count
    }





@app.post("/downgrade")
async def downgrade_tier(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """
    Allow users to downgrade to the free tier.
    Note: Credits remain as they were, but the tier changes.
    """
    if current_user.tier == "free":
        return {"status": "ignored", "message": "Already on free tier"}
    
    current_user.tier = "free"
    db.commit()
    return {"status": "success", "message": "Subscription cancelled. Downgraded to free tier."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

