
from fastapi import FastAPI, Depends, HTTPException, status, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from fastapi.responses import JSONResponse, RedirectResponse

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
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    logger.info("Sentry initialized.")



try:
    from backend.db import SessionLocal, engine, get_db, DATABASE_URL
    from backend.models import Quote, Analytics, FeedItem, Base, Users, UserMemory
    from backend.embeddings import embed_text, cosine_sim, HAS_MODEL
    from backend.redis_client import get_cached_search, cache_search, get_conversation, save_conversation, HAS_REDIS, REDIS_URL
    from backend.generation import generate_quote, generate_response
    from backend.image_gen import generate_quote_image
except ImportError:
    from db import SessionLocal, engine, get_db, DATABASE_URL
    from models import Quote, Analytics, FeedItem, Base, Users, UserMemory
    from embeddings import embed_text, cosine_sim, HAS_MODEL
    from redis_client import get_cached_search, cache_search, get_conversation, save_conversation, HAS_REDIS, REDIS_URL
    from generation import generate_quote, generate_response
    from image_gen import generate_quote_image



import numpy as np

import hashlib

import base64

from io import BytesIO

from typing import List, Optional

from sqlalchemy import func

import asyncio

from concurrent.futures import ThreadPoolExecutor



_executor = ThreadPoolExecutor(max_workers=4)



SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-prod")

CLIENT_KEY = os.getenv("CLIENT_KEY")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



# Empty in-memory user store — no hashing at module level
# users_db = {}





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
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
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





limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="LEVI Quotes API")

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



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
    "https://levi-aicreate.app",
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
    allow_credentials=not allow_all,
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





@app.get("/")

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

         "similarity": 0.9, "search_mode": "semantic" if HAS_MODEL else "random_fallback"}

        for q in results

    ]

    cache_search(query_hash, formatted)

    return formatted





@app.post("/generate")

def gen_quote(prompt: Query):

    generated = generate_quote(prompt.text, mood=prompt.mood or "")

    return {"generated_quote": generated}





@app.post("/generate_image")

async def gen_image(req: Query, db: Session = Depends(get_db)):

    try:

        loop = asyncio.get_event_loop()

        bio = await loop.run_in_executor(

            _executor,

            lambda: generate_quote_image(req.text, author=req.author or "Unknown",

                                          mood=req.mood or "neutral", custom_bg=req.custom_bg),

        )

        img_b64 = base64.b64encode(bio.getvalue()).decode()

        img_data = f"data:image/png;base64,{img_b64}"

        new_feed = FeedItem(text=req.text, author=req.author or "Unknown",

                            mood=req.mood or "neutral", image_b64=img_data, likes=0)

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
        mood="", 
        lang=msg.lang or "en",
        user_memory=user_mem
    )
    
    history.append({"user": msg.message, "bot": bot_response})
    save_conversation(msg.session_id, history)
    return {"response": bot_response}





@app.post("/register", response_model=Token)
async def register(user_in: UserIn, db: Session = Depends(get_db)):
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





if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

