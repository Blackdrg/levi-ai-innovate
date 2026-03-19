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
try:
    from backend.db import SessionLocal, engine, get_db, DATABASE_URL
    from backend.models import Quote, Analytics
    from backend.embeddings import embed_text, cosine_sim
    from backend.redis_client import get_cached_search, cache_search, get_conversation, save_conversation
    from backend.generation import generate_quote, generate_response
    from backend.image_gen import generate_quote_image
except ImportError:
    from db import SessionLocal, engine, get_db, DATABASE_URL
    from models import Quote, Analytics
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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func
import asyncio
from concurrent.futures import ThreadPoolExecutor

print("Starting LEVI backend...")
load_dotenv()

executor = ThreadPoolExecutor(max_workers=3)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

users_db = {"testuser": {
    "username": "testuser",
    "hashed_password": pwd_context.hash("testpass"),
}}

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
    top_k: int = 5

class ChatMessage(BaseModel):
    session_id: str
    message: str

# No Base.metadata.create_all here, handled in db.py if needed

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="LEVI Quotes API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "search_mode": "pgvector" if "postgresql" in DATABASE_URL else "sqlite-memory"
    }

@app.get("/daily_quote")
def daily_quote(db: Session = Depends(get_db)):
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

    # 2. Embed Query
    query_embedding = embed_text(query.text)
    
    # 3. Vector Search
    if "postgresql" in DATABASE_URL:
        results = db.query(Quote).order_by(Quote.embedding.l2_distance(query_embedding)).limit(query.top_k).all()
    else:
        # Fallback for SQLite: In-memory search
        all_quotes = db.query(Quote).all()
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
async def gen_image(req: Query):
    loop = asyncio.get_event_loop()
    bio = await loop.run_in_executor(
        executor, 
        generate_quote_image, 
        req.text, 
        req.author or "Unknown", 
        req.mood or "neutral"
    )
    img_b64 = base64.b64encode(bio.getvalue()).decode()
    return {"image_b64": f"data:image/png;base64,{img_b64}"}

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, msg: ChatMessage, db: Session = Depends(get_db)):
    print(f"Chat request received: {msg.message}")
    today = date.today()
    analytics = db.query(Analytics).filter(Analytics.date == today).first()
    if not analytics:
        analytics = Analytics(date=today, chats_count=0, likes_count=0, daily_users=0)
        db.add(analytics)
    
    if analytics.chats_count is None:
        analytics.chats_count = 0
    analytics.chats_count += 1
    db.commit()
    
    # Get conversation history
    history = get_conversation(msg.session_id)
    
    # Try RASA first
    try:
        rasa_resp = requests.post(
            "http://rasa-server:5005/webhooks/rest/webhook",
            json={"sender": msg.session_id, "message": msg.message},
            timeout=2 # Short timeout
        )
        if rasa_resp.status_code == 200:
            responses = rasa_resp.json()
            if responses:
                bot_response = " ".join([r.get("text", "") for r in responses])
                # Store and return
                history.append({"user": msg.message, "bot": bot_response})
                save_conversation(msg.session_id, history)
                return {"response": bot_response}
    except Exception:
        pass # Fallback to LLM/Search if RASA fails

    # NLP Fallback: Use GPT-2 with history context
    # But first, check if it's a specific request for a quote
    quote_keywords = ["quote", "inspiration", "wisdom", "motto", "saying"]
    is_quote_request = any(kw in msg.message.lower() for kw in quote_keywords)
    
    if is_quote_request:
        query_embedding = embed_text(msg.message)
        if "postgresql" in DATABASE_URL:
            best_quote = db.query(Quote).order_by(Quote.embedding.l2_distance(query_embedding)).first()
        else:
            # Fallback for SQLite
            all_quotes = db.query(Quote).all()
            q_emb = np.array(query_embedding)
            best_quote = None
            best_sim = -1
            for q in all_quotes:
                if q.embedding is not None:
                    sim = cosine_sim(q_emb, np.array(q.embedding))
                    if sim > best_sim:
                        best_sim = sim
                        best_quote = q
        
        if best_quote:
            bot_response = f"I found a quote that might inspire you: '{best_quote.text}' - {best_quote.author}"
        else:
            bot_response = generate_quote(msg.message)
    else:
        # It's a general conversational message
        bot_response = generate_response(msg.message, history=history)
    
    # Store in history
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
