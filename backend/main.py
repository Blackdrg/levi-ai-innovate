from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, date
import os
import requests
from dotenv import load_dotenv

# Ensure environment variables are loaded at the very beginning
load_dotenv()

try:
    from backend.db import SessionLocal, engine, get_db, DATABASE_URL
    from backend.models import Quote, Analytics, FeedItem, Base
    from backend.embeddings import embed_text, cosine_sim
    from backend.redis_client import get_cached_search, cache_search, get_conversation, save_conversation
    from backend.generation import generate_quote, generate_response
    from backend.image_gen import generate_quote_image
except ImportError:
    from db import SessionLocal, engine, get_db, DATABASE_URL
    from models import Quote, Analytics, FeedItem, Base
    from embeddings import embed_text, cosine_sim
    from redis_client import get_cached_search, cache_search, get_conversation, save_conversation
    from generation import generate_quote, generate_response
    from image_gen import generate_quote_image
import numpy as np
import hashlib
import json
import base64
from io import BytesIO
from typing import List, Optional
from PIL import Image
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func

print("Starting LEVI backend...")

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-prod")
CLIENT_KEY = os.getenv("CLIENT_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# users_db = {"testuser": {
#     "username": "testuser",
#     "hashed_password": pwd_context.hash("testpass"),
# }}
users_db = {}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
    custom_bg: Optional[str] = None  # Base64 or URL
    top_k: int = 5

class ChatMessage(BaseModel):
    session_id: str
    message: str
    lang: Optional[str] = "en"

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="LEVI Quotes API")
app.state.limiter = limiter

# Allow CORS for development and production
env_origins = os.getenv("CORS_ORIGINS", "").split(",")
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://levi-git-main-daksh-mehats-projects.vercel.app",
    "https://levi-k8iuadcvd-daksh-mehats-projects.vercel.app",
    "https://levi-ai.vercel.app",  # Common production pattern
]
# Add origins from environment variables if present
if env_origins:
    for o in env_origins:
        origin = o.strip()
        if origin and origin != "*" and origin not in origins:
            origins.append(origin)

# Handle wildcard correctly for allow_credentials=True
allow_all = "*" in env_origins or os.getenv("CORS_ORIGINS") == "*"


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=not allow_all, # credentials cannot be used with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse

# Global exception handler for better stability
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Global error: {exc}")
    import traceback
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Our creative circuits are being realigned."},
    )

@app.on_event("startup")
async def startup_event():
    logging.info("Starting LEVI backend... Model loading triggered in background.")
    
    # Check for Redis connection
    from redis_client import HAS_REDIS, REDIS_URL
    if not HAS_REDIS:
        logging.warning("REDIS_URL is not set or connection failed. Session persistence and caching will be limited.")
    else:
        logging.info(f"Redis connected successfully (masked: {REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL})")
    
    # Create tables on startup
    try:
        logging.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables initialized successfully.")
    except Exception as e:
        logging.error(f"Error creating tables on startup: {e}")

    # Debug: Log environment info
    logging.info(f"CORS origins: {origins}")
    logging.info(f"Database URL scheme: {DATABASE_URL.split('://')[0] if DATABASE_URL else 'None'}")
    logging.info(f"CLIENT_KEY is {'SET' if CLIENT_KEY else 'NOT SET'}")

@app.get("/")
def read_root():
    return {"message": "Welcome to LEVI AI API", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/daily_quote")
def daily_quote(db: Session = Depends(get_db)):
    # 1. Try Open Source API first for fresh daily wisdom
    from backend.generation import fetch_open_source_quote
    os_quote = fetch_open_source_quote()
    if os_quote:
        return {"quote": os_quote['quote'], "author": os_quote['author']}

    # 2. Fallback to DB
    today_quotes = db.query(Quote).order_by(func.random()).first()
    if not today_quotes:
        return {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"}
    return {"quote": today_quotes.text, "author": today_quotes.author}

@app.get("/analytics", response_model=dict)
def get_analytics(db: Session = Depends(get_db)):
    today = date.today()
    total_chats = db.query(func.sum(Analytics.chats_count)).scalar() or 0
    popular_topics = db.query(Quote.topic, func.count(Quote.id)).group_by(Quote.topic).order_by(func.count(Quote.id).desc()).limit(5).all()
    popular_topics_list = [topic for topic, count in popular_topics if topic]
    return {
        "total_chats": total_chats,
        "daily_users": 0,
        "popular_topics": popular_topics_list,
        "likes_count": 0
    }

@app.post("/search_quotes", response_model=List[dict])
def search_quotes(query: Query, db: Session = Depends(get_db)):
    # 1. Check Cache
    query_hash = hashlib.md5(f"{query.text}:{query.mood}:{query.topic}".encode()).hexdigest()
    cached = get_cached_search(query_hash)
    if cached:
        return cached

    if not query.text:
        # Return random quotes if no query
        results = db.query(Quote).order_by(func.random()).limit(query.top_k).all()
    else:
        # 2. Embed Query
        query_embedding = embed_text(query.text)
        
        # 3. Vector Search
        if "postgresql" in DATABASE_URL:
            base_query = db.query(Quote)
            if query.mood:
                base_query = base_query.filter(Quote.mood == query.mood)
            results = base_query.order_by(Quote.embedding.l2_distance(query_embedding)).limit(query.top_k).all()
        else:
            # Fallback for SQLite: In-memory search
            all_quotes_query = db.query(Quote)
            if query.mood:
                all_quotes_query = all_quotes_query.filter(Quote.mood == query.mood)
            all_quotes = all_quotes_query.all()
            
            q_emb = np.array(query_embedding)
            scored = []
            for q in all_quotes:
                if q.embedding is not None:
                    sim = cosine_sim(q_emb, np.array(q.embedding))
                    scored.append((q, sim))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [s[0] for s in scored[:query.top_k]]
    
    formatted_results = [
        {"quote": q.text, "author": q.author, "topic": q.topic, "mood": q.mood, "similarity": 0.9} 
        for q in results
    ]
    
    # 4. Cache Results
    cache_search(query_hash, formatted_results)
    
    return formatted_results

@app.post("/generate")
def gen_quote(prompt: Query):
    generated = generate_quote(prompt.text, mood=prompt.mood or "")
    return {"generated_quote": generated}

@app.post("/generate_image")
def gen_image(req: Query, db: Session = Depends(get_db)):
    try:
        bio = generate_quote_image(
            req.text, 
            author=req.author or "Unknown", 
            mood=req.mood or "neutral",
            custom_bg=req.custom_bg
        )
        img_b64 = base64.b64encode(bio.getvalue()).decode()
        img_data = f"data:image/png;base64,{img_b64}"
        
        # Add to public feed
        new_feed = FeedItem(
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
        logging.error(f"Image generation error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/like/{item_type}/{item_id}")
def like_item(item_type: str, item_id: int, db: Session = Depends(get_db)):
    """Handles liking both quotes and feed items (images)."""
    if item_type == "quote":
        item = db.query(Quote).filter(Quote.id == item_id).first()
    elif item_type == "feed":
        item = db.query(FeedItem).filter(FeedItem.id == item_id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid item type")
        
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    item.likes = (item.likes or 0) + 1
    
    # Update global analytics
    today = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if analytics:
        analytics.likes_count = (analytics.likes_count or 0) + 1
    
    db.commit()
    return {"status": "success", "new_likes": item.likes}

@app.get("/feed", response_model=List[dict])
def get_feed(db: Session = Depends(get_db), limit: int = 20):
    items = db.query(FeedItem).order_by(FeedItem.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": i.id,
            "text": i.text,
            "author": i.author,
            "mood": i.mood,
            "image": i.image_b64,
            "likes": i.likes or 0,
            "time": i.timestamp.isoformat()
        } for i in items
    ]

import logging

logging.basicConfig(level=logging.INFO)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, msg: ChatMessage, db: Session = Depends(get_db)):
    """
    Main chat endpoint.
    Uses a unified generation model to handle both conversation and quote generation.
    """
    logging.info(f"Chat request received for session {msg.session_id}: '{msg.message}'")

    # Increment analytics
    today = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if not analytics:
        analytics = Analytics(date=today, chats_count=1)
        db.add(analytics)
    else:
        analytics.chats_count = (analytics.chats_count or 0) + 1
    db.commit()

    # Get conversation history
    history = get_conversation(msg.session_id)

    # Generate a contextual response using the improved generation function
    bot_response = generate_response(msg.message, history=history, mood=msg.mood if hasattr(msg, 'mood') else '', lang=msg.lang or 'en')
    logging.info(f"Generated response: {bot_response}")

    # Save the new exchange to history
    history.append({"user": msg.message, "bot": bot_response})
    save_conversation(msg.session_id, history)

    return {"response": bot_response}

@app.post("/register", response_model=Token)
async def register(user_in: UserIn):
    hashed_password = get_password_hash(user_in.password)
    users_db[user_in.username] = {"username": user_in.username, "hashed_password": hashed_password}
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user_in.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

if __name__ == "__main__":
    import uvicorn
    print("Starting uvicorn...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
