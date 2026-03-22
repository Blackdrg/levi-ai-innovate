
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from starlette.routing import Route

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from sqlalchemy.orm import Session

from pydantic import BaseModel

from jose import JWTError, jwt

from passlib.context import CryptContext

from datetime import datetime, timedelta, date

from slowapi import Limiter

from slowapi.util import get_remote_address

from slowapi.errors import RateLimitExceeded

from slowapi import _rate_limit_exceeded_handler
from authlib.integrations.starlette_client import OAuth
import os

import logging

import requests

from dotenv import load_dotenv



import sentry_sdk

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    "RAZORPAY_WEBHOOK_SECRET"
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
    from backend.models import Quote, Analytics, FeedItem, Base, Users, UserMemory, ChatHistory
    from backend.embeddings import embed_text, cosine_sim, HAS_MODEL
    from backend.redis_client import get_cached_search, cache_search, get_conversation, save_conversation, HAS_REDIS, REDIS_URL
    from backend.generation import generate_quote, generate_response
    from backend.image_gen import generate_quote_image
    from backend.video_gen import generate_quote_video
    from backend.email_service import send_daily_quote
    from backend.payments import router as payments_router, use_credits, verify_payment_signature
    from backend.tasks import generate_video_task as generate_video_async
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Could not import from backend.*: {e}. Falling back to local imports.")
    try:
        from db import SessionLocal, engine, get_db, DATABASE_URL
        from models import Quote, Analytics, FeedItem, Base, Users, UserMemory, ChatHistory
        from embeddings import embed_text, cosine_sim, HAS_MODEL
        from redis_client import get_cached_search, cache_search, get_conversation, save_conversation, HAS_REDIS, REDIS_URL
        from generation import generate_quote, generate_response
        from image_gen import generate_quote_image
        from video_gen import generate_quote_video
        from email_service import send_daily_quote
        from payments import router as payments_router, use_credits, verify_payment_signature
        from tasks import generate_video_task as generate_video_async
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

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-prod")
CLIENT_KEY = os.getenv("CLIENT_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days for better user experience

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        raise credentials_exception
    return user

class User(BaseModel):
    username: str

class UserIn(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Query(BaseModel):
    text: str
    author: Optional[str] = None
    mood: Optional[str] = None
    topic: Optional[str] = None
    lang: Optional[str] = "en"
    custom_bg: Optional[str] = None
    top_k: int = 5

class ChatMessage(BaseModel):
    session_id: str
    message: str
    lang: Optional[str] = "en"
    mood: Optional[str] = ""

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
app.include_router(payments_router)

# Rate Limiter setup
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

    o = o.strip()

    if o and o != "*" and o not in origins:

        origins.append(o)



allow_all = "*" in env_origins or os.getenv("CORS_ORIGINS") == "*"



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=False if allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                password_hash=get_password_hash(os.urandom(16).hex()) # Random password for OAuth users
            )
            db.add(user)
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

            scored = [(q, cosine_sim(q_emb, np.array(q.embedding))) for q in all_quotes if q.embedding is not None]

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
async def gen_image(request: Request, req: Query, db: Session = Depends(get_db), current_user: Optional[Users] = Depends(get_current_user)):
    try:
        user_id = current_user.id if current_user else None
        user_tier = current_user.tier if current_user else "free"
        
        # Security: Validate custom_bg if provided
        if req.custom_bg:
            # Check size (approximate for base64)
            if len(req.custom_bg) > 7 * 1024 * 1024: # ~5MB after decoding
                raise HTTPException(status_code=400, detail="Custom background exceeds 5MB limit")
            
            # Basic type check
            if not req.custom_bg.startswith("data:image/"):
                raise HTTPException(status_code=400, detail="Invalid image format. Must be a data URI.")
        
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
                custom_bg=req.custom_bg,
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

def get_feed(db: Session = Depends(get_db), limit: int = 20):

    items = db.query(FeedItem).order_by(FeedItem.timestamp.desc()).limit(limit).all()

    return [{"id": i.id, "text": i.text, "author": i.author, "mood": i.mood,

            "image": i.image_b64, "likes": i.likes or 0, "time": i.timestamp.isoformat()}

            for i in items]





@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, msg: ChatMessage, db: Session = Depends(get_db), current_user: Optional[Users] = Depends(get_current_user)):
    # Try to identify user if authenticated
    user_id = current_user.id if current_user else None
    
    logger.info(f"Chat [{msg.session_id}] (User: {user_id}): '{msg.message[:60]}'")
    today = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if not analytics:
        analytics = Analytics(date=today, chats_count=1)
        db.add(analytics)
    else:
        analytics.chats_count = (analytics.chats_count or 0) + 1
    
    # Update user memory if authenticated
    user_mem = None
    if user_id:
        user_mem = db.query(UserMemory).filter(UserMemory.user_id == user_id).first()
        if not user_mem:
            user_mem = UserMemory(user_id=user_id, mood_history=[], liked_topics=[], interaction_count=0)
            db.add(user_mem)
        user_mem.interaction_count += 1
        # Simple heuristic for mood/topic extraction (can be improved with LLM later)
        # For now, we'll let generate_response handle the logic if needed, 
        # but we track the interaction here.
    
    db.commit()
    
    history = get_conversation(msg.session_id)
    
    # Pass user memory to generation if available
    bot_response = generate_response(
        msg.message, 
        history=history, 
        mood=msg.mood or "", 
        lang=msg.lang or "en",
        user_memory=user_mem
    )
    
    history.append({"user": msg.message, "bot": bot_response})
    save_conversation(msg.session_id, history)
    return {"response": bot_response}





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

@app.post("/register", response_model=Token)
async def register(user_in: UserIn, db: Session = Depends(get_db)):
    if len(user_in.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    existing = db.query(Users).filter(Users.username == user_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user = Users(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password)
    )
    db.add(user)
    db.commit()
    
    token = create_access_token(data={"sub": user.username},
                                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
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
        return {
            "status": "completed",
            "result": result
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
async def get_my_gallery(db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """Fetch all generated items for the current user."""
    items = db.query(FeedItem).filter(FeedItem.user_id == current_user.id).order_by(FeedItem.timestamp.desc()).all()
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
    from backend.payments import upgrade_user_tier
    valid = verify_payment_signature(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    
    # Upgrade user tier in DB
    upgrade_user_tier(current_user.id, data.plan, db) 
    
    return {"status": "success", "message": f"Payment confirmed and account upgraded to {data.plan}"}

@app.post("/razorpay_webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Razorpay webhooks for payment.captured events.
    """
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    if not secret or not signature:
        logger.warning("Razorpay webhook missing secret or signature")
        return {"status": "ignored"}

    # Verify webhook signature
    expected_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
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
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")
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
            upgrade_user_tier(int(user_id), plan, db)
            
            # Audit Trail: Log payment success
            logger.info(f"[PAYMENT_SUCCESS] User: {user_id} | Amount: {amount} INR | Plan: {plan} | Order: {order_id} | Payment: {payment_id}")
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





if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

