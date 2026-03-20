import os
import logging
import hashlib
import base64
import json
from io import BytesIO
from datetime import datetime, timedelta, date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import numpy as np
import requests as http_requests
from PIL import Image
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Imports — hybrid local/package
# ─────────────────────────────────────────────
try:
    from backend.db import SessionLocal, engine, get_db, DATABASE_URL
    from backend.models import Quote, Analytics, FeedItem, Base, Users, UserMemory
    from backend.embeddings import embed_text, cosine_sim
    from backend.redis_client import get_cached_search, cache_search, get_conversation, save_conversation
    from backend.generation import generate_quote, generate_response
    from backend.image_gen import generate_quote_image
    from backend.payments import router as payments_router, use_credits
except ImportError:
    from db import SessionLocal, engine, get_db, DATABASE_URL
    from models import Quote, Analytics, FeedItem, Base, Users, UserMemory
    from embeddings import embed_text, cosine_sim
    from redis_client import get_cached_search, cache_search, get_conversation, save_conversation
    from generation import generate_quote, generate_response
    from image_gen import generate_quote_image
    from payments import router as payments_router, use_credits

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
SECRET_KEY                 = os.getenv("SECRET_KEY", "")
ALGORITHM                  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

if not SECRET_KEY:
    if os.getenv("RENDER") == "true":
        raise RuntimeError("CRITICAL: SECRET_KEY must be set in production!")
    SECRET_KEY = "dev-only-insecure-key-change-before-deploy"
    logger.warning("SECRET_KEY not set — using insecure default (dev only)")

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app     = FastAPI(
    title       = "LEVI AI API",
    description = "Creative AI platform — quotes, visuals, wisdom",
    version     = "2.1.0",
    docs_url    = "/docs" if os.getenv("RENDER") != "true" else None,  # Hide docs in prod
)
app.state.limiter = limiter

# ── Mount payments router ──────────────────
app.include_router(payments_router)

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────
_raw_origins = os.getenv("CORS_ORIGINS", "").strip()
_allow_all   = _raw_origins == "*"

_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "https://levi-git-main-daksh-mehats-projects.vercel.app",
    "https://levi-k8iuadcvd-daksh-mehats-projects.vercel.app",
    "https://levi-ai.vercel.app",
]
for _o in _raw_origins.split(","):
    _o = _o.strip()
    if _o and _o != "*" and _o not in _origins:
        _origins.append(_o)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"] if _allow_all else _origins,
    allow_credentials = False,
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers     = ["*"],
)

# ─────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────
class UserIn(BaseModel):
    username: str
    password: str
    email:    Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type:   str

class Query(BaseModel):
    text:      str
    author:    Optional[str] = None
    mood:      Optional[str] = None
    topic:     Optional[str] = None
    lang:      Optional[str] = "en"
    custom_bg: Optional[str] = None
    top_k:     int = 5

class ChatMessage(BaseModel):
    session_id: str
    message:    str
    lang:       Optional[str] = "en"
    user_id:    Optional[int] = None

# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    payload = data.copy()
    expire  = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db)
) -> Optional[Users]:
    if not token:
        return None
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return db.query(Users).filter(Users.username == username).first()
    except JWTError:
        return None

# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("LEVI backend starting up...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready.")
    except Exception as e:
        logger.error(f"DB init error: {e}")

    from backend.redis_client import HAS_REDIS
    logger.info(f"Redis: {'connected' if HAS_REDIS else 'fallback in-memory'}")
    logger.info(f"DB scheme: {DATABASE_URL.split('://')[0]}")
    logger.info(f"Together.AI: {'configured' if os.getenv('TOGETHER_API_KEY') else 'NOT SET — using fallback'}")
    logger.info(f"Stripe: {'configured' if os.getenv('STRIPE_SECRET_KEY') else 'NOT SET'}")
    logger.info(f"S3: {'configured' if os.getenv('AWS_S3_BUCKET') else 'NOT SET — local storage'}")

# ─────────────────────────────────────────────
# Global exception handler
# ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Our circuits are being realigned."}
    )

# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "LEVI AI is running", "version": "2.1.0"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.1.0"}

# ─────────────────────────────────────────────
# Auth routes — now uses real DB
# ─────────────────────────────────────────────
@app.post("/register", response_model=Token)
async def register(user_in: UserIn, db: Session = Depends(get_db)):
    # Check duplicate username
    if db.query(Users).filter(Users.username == user_in.username).first():
        raise HTTPException(400, "Username already taken")
    # Check duplicate email
    if user_in.email and db.query(Users).filter(Users.email == user_in.email).first():
        raise HTTPException(400, "Email already registered")

    user = Users(
        username      = user_in.username,
        email         = user_in.email,
        password_hash = hash_password(user_in.password),
        tier          = "free",
        credits       = 10,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        {"sub": user.username},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}


@app.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db:        Session = Depends(get_db)
):
    user = db.query(Users).filter(Users.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        {"sub": user.username},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/users/me")
async def get_me(current_user: Users = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(401, "Not authenticated")
    return {
        "id":       current_user.id,
        "username": current_user.username,
        "email":    current_user.email,
        "tier":     current_user.tier,
        "credits":  current_user.credits,
    }

# ─────────────────────────────────────────────
# Daily quote
# ─────────────────────────────────────────────
@app.get("/daily_quote")
def daily_quote(db: Session = Depends(get_db)):
    try:
        from backend.generation import fetch_open_source_quote
        q = fetch_open_source_quote()
        if q:
            return q
    except Exception:
        pass
    row = db.query(Quote).order_by(func.random()).first()
    if row:
        return {"quote": row.text, "author": row.author}
    return {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"}

# ─────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────
@app.post("/search_quotes", response_model=List[dict])
def search_quotes(query: Query, db: Session = Depends(get_db)):
    qhash  = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()
    cached = get_cached_search(qhash)
    if cached:
        return cached

    if not query.text:
        results = db.query(Quote).order_by(func.random()).limit(query.top_k).all()
    else:
        q_emb = embed_text(query.text)
        if "postgresql" in DATABASE_URL:
            base_q = db.query(Quote)
            if query.mood:
                base_q = base_q.filter(Quote.mood == query.mood)
            results = base_q.order_by(Quote.embedding.l2_distance(q_emb)).limit(query.top_k).all()
        else:
            all_q = db.query(Quote)
            if query.mood:
                all_q = all_q.filter(Quote.mood == query.mood)
            scored = []
            for q in all_q.all():
                if q.embedding is not None:
                    sim = cosine_sim(np.array(q_emb), np.array(q.embedding))
                    scored.append((q, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [s[0] for s in scored[:query.top_k]]

    formatted = [
        {"quote": q.text, "author": q.author, "topic": q.topic, "mood": q.mood, "similarity": 0.9}
        for q in results
    ]
    cache_search(qhash, formatted)
    return formatted

# ─────────────────────────────────────────────
# Generate quote text
# ─────────────────────────────────────────────
@app.post("/generate")
def gen_quote(prompt: Query):
    generated = generate_quote(prompt.text, mood=prompt.mood or "")
    return {"generated_quote": generated}

# ─────────────────────────────────────────────
# Generate image — credit-gated
# ─────────────────────────────────────────────
@app.post("/generate_image")
def gen_image(
    req:          Query,
    db:           Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user)
):
    # Deduct 2 credits for free users
    if current_user:
        use_credits(current_user.id, 2, db)

    try:
        bio     = generate_quote_image(req.text, req.author or "Unknown", req.mood or "neutral", custom_bg=req.custom_bg)
        img_b64 = "data:image/png;base64," + base64.b64encode(bio.getvalue()).decode()

        # Try S3 upload for persistent storage
        s3_url = None
        if os.getenv("AWS_S3_BUCKET") and current_user:
            try:
                from backend.tasks import upload_image_to_s3
                s3_url = upload_image_to_s3(bio.getvalue(), current_user.id)
            except Exception as e:
                logger.warning(f"S3 upload skipped: {e}")

        feed = FeedItem(
            text      = req.text,
            author    = req.author or "Unknown",
            mood      = req.mood or "neutral",
            image_b64 = img_b64,
            image_url = s3_url,
            likes     = 0,
        )
        db.add(feed)
        db.commit()
        db.refresh(feed)

        return {"id": feed.id, "image_b64": img_b64, "image_url": s3_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation error: {e}", exc_info=True)
        raise HTTPException(500, "Image generation failed. Please try again.")

# ─────────────────────────────────────────────
# Generate video (async task)
# ─────────────────────────────────────────────
@app.post("/generate_video")
def gen_video(
    req:          Query,
    db:           Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(401, "Login required to generate videos.")
    if current_user.tier not in ("pro", "creator"):
        raise HTTPException(402, {
            "error":   "upgrade_required",
            "message": "Video generation requires Pro or Creator plan.",
            "upgrade": "/pricing"
        })

    try:
        from backend.tasks import generate_video_task
        task = generate_video_task.delay(req.text, req.author or "LEVI AI", req.mood or "neutral", current_user.id)
        return {"task_id": task.id, "status": "processing", "message": "Your video is being created. Check back in ~30 seconds."}
    except Exception as e:
        logger.error(f"Video task error: {e}")
        raise HTTPException(500, "Failed to queue video generation.")

@app.get("/task_status/{task_id}")
def task_status(task_id: str):
    try:
        from backend.tasks import celery_app
        result = celery_app.AsyncResult(task_id)
        if result.ready():
            return {"status": "done", "result": result.get()}
        return {"status": result.state.lower()}
    except Exception:
        return {"status": "unknown"}

# ─────────────────────────────────────────────
# Likes
# ─────────────────────────────────────────────
@app.post("/like/{item_type}/{item_id}")
def like_item(item_type: str, item_id: int, db: Session = Depends(get_db)):
    model = Quote if item_type == "quote" else FeedItem if item_type == "feed" else None
    if not model:
        raise HTTPException(400, "Invalid item type")
    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    item.likes = (item.likes or 0) + 1

    today     = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if analytics:
        analytics.likes_count = (analytics.likes_count or 0) + 1
    db.commit()
    return {"status": "success", "new_likes": item.likes}

# ─────────────────────────────────────────────
# Feed
# ─────────────────────────────────────────────
@app.get("/feed", response_model=List[dict])
def get_feed(db: Session = Depends(get_db), limit: int = 20):
    items = db.query(FeedItem).order_by(FeedItem.timestamp.desc()).limit(limit).all()
    return [
        {
            "id":     i.id,
            "text":   i.text,
            "author": i.author,
            "mood":   i.mood,
            "image":  i.image_url or i.image_b64,  # Prefer S3 URL
            "likes":  i.likes or 0,
            "time":   i.timestamp.isoformat(),
        }
        for i in items
    ]

# ─────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────
@app.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    total_chats    = db.query(func.sum(Analytics.chats_count)).scalar() or 0
    popular_topics = (
        db.query(Quote.topic, func.count(Quote.id))
        .group_by(Quote.topic)
        .order_by(func.count(Quote.id).desc())
        .limit(5)
        .all()
    )
    return {
        "total_chats":    total_chats,
        "popular_topics": [t for t, _ in popular_topics if t],
        "likes_count":    db.query(func.sum(Analytics.likes_count)).scalar() or 0,
    }

# ─────────────────────────────────────────────
# Chat — rate limited
# ─────────────────────────────────────────────
@app.post("/chat")
@limiter.limit("20/minute")
async def chat(
    request:      Request,
    msg:          ChatMessage,
    db:           Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user)
):
    logger.info(f"Chat [{msg.session_id}]: {msg.message[:60]}")

    # Analytics
    today     = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if not analytics:
        analytics = Analytics(date=today, chats_count=1)
        db.add(analytics)
    else:
        analytics.chats_count = (analytics.chats_count or 0) + 1
    db.commit()

    # Deduct 1 credit for free users
    if current_user:
        use_credits(current_user.id, 1, db)

    history     = get_conversation(msg.session_id)
    bot_response = generate_response(
        msg.message,
        history  = history,
        mood     = "",
        lang     = msg.lang or "en"
    )

    history.append({"user": msg.message, "bot": bot_response})
    save_conversation(msg.session_id, history)

    # Update user memory
    if current_user:
        try:
            memory = db.query(UserMemory).filter(UserMemory.user_id == current_user.id).first()
            if not memory:
                memory = UserMemory(user_id=current_user.id)
                db.add(memory)
            memory.interaction_count = (memory.interaction_count or 0) + 1
            memory.last_active       = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.warning(f"Memory update failed: {e}")

    return {"response": bot_response}

# ─────────────────────────────────────────────
# Pricing info (for frontend)
# ─────────────────────────────────────────────
@app.get("/pricing")
def get_pricing():
    return {
        "plans": [
            {
                "id":          "free",
                "name":        "Free",
                "price":       0,
                "currency":    "INR",
                "credits":     10,
                "features":    ["10 generations/month", "Basic AI chat", "Public feed access"],
            },
            {
                "id":          "pro",
                "name":        "Pro",
                "price":       499,
                "currency":    "INR",
                "credits":     300,
                "stripe_price": os.getenv("STRIPE_PRICE_PRO", ""),
                "features":    ["300 HD generations/month", "Advanced AI", "No watermark", "Priority processing"],
                "popular":     True,
            },
            {
                "id":          "creator",
                "name":        "Creator",
                "price":       1499,
                "currency":    "INR",
                "credits":     -1,
                "stripe_price": os.getenv("STRIPE_PRICE_CREATOR", ""),
                "features":    ["Unlimited everything", "Video generation", "Voice narration", "Analytics"],
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
