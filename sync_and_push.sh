#!/usr/bin/env bash

# sync_and_push.sh

# Run this from the ROOT of your LEVI repo.

# It overwrites ALL backend files with the fixed versions, then pushes.

set -e



echo "=== LEVI — Full sync to GitHub ==="



if [ ! -d ".git" ]; then

  echo "ERROR: Run from the root of your LEVI git repo."

  exit 1

fi



# ── Confirm we're in the right place ────────────────────────────────────────

if [ ! -d "backend" ] || [ ! -d "frontend" ]; then

  echo "ERROR: Expected to find backend/ and frontend/ directories here."

  exit 1

fi



echo "Repo root: $(pwd)"

echo "Overwriting all backend files with fixed versions..."



# ── Write requirements.txt ───────────────────────────────────────────────────

cat > backend/requirements.txt << 'REQEOF'

fastapi>=0.110.0

uvicorn[standard]>=0.29.0

gunicorn>=22.0.0

sqlalchemy>=2.0.30

psycopg2-binary>=2.9.9

redis>=5.0.4

# transformers 5.x removed pipeline from top-level — must stay on 4.x

transformers>=4.40.0,<5.0.0

sentence-transformers>=3.0.0,<4.0.0

--extra-index-url https://download.pytorch.org/whl/cpu

torch>=2.2.0,<3.0.0

torchvision>=0.17.0

torchaudio>=2.2.0

pillow>=10.3.0

python-jose[cryptography]>=3.3.0

# bcrypt 5.x broke passlib 1.7.4 API — pin bcrypt to 4.x

passlib[bcrypt]>=1.7.4

bcrypt>=4.0.0,<5.0.0

python-dotenv>=1.0.1

pydantic>=2.7.0

pgvector>=0.3.0

numpy>=1.26.4

scikit-learn>=1.4.0

slowapi>=0.1.9

pytest>=8.2.0

httpx>=0.27.0

pytest-asyncio>=0.23.6

requests>=2.31.0

mtranslate>=1.8

waitress>=3.0.0

python-multipart>=0.0.9

REQEOF

echo "  ✓ requirements.txt"



# ── Write models.py ──────────────────────────────────────────────────────────

cat > backend/models.py << 'MODELEOF'

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, UniqueConstraint

from sqlalchemy.sql import func



try:

    from sqlalchemy.dialects.postgresql import VECTOR

    HAS_PGVECTOR = True

except ImportError:

    HAS_PGVECTOR = False



try:

    from backend.db import Base, DATABASE_URL

except ImportError:

    from db import Base, DATABASE_URL



from sqlalchemy import PickleType





class Quote(Base):

    __tablename__ = "quotes"

    __table_args__ = (

        UniqueConstraint("text", name="uq_quote_text"),

    )



    id = Column(Integer, primary_key=True, index=True)

    text = Column(String, nullable=False)

    author = Column(String)

    topic = Column(String)

    mood = Column(String)

    likes = Column(Integer, default=0)



    if HAS_PGVECTOR and "postgresql" in DATABASE_URL:

        embedding = Column(VECTOR(384))

    else:

        embedding = Column(PickleType)



    created_at = Column(DateTime(timezone=True), server_default=func.now())





class Users(Base):

    __tablename__ = "users"



    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, index=True, nullable=False)

    password_hash = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())





class ChatHistory(Base):

    __tablename__ = "chat_history"



    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    message = Column(String, nullable=False)

    response = Column(String, nullable=False)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())





class FeedItem(Base):

    __tablename__ = "feed_items"



    id = Column(Integer, primary_key=True, index=True)

    text = Column(String)

    author = Column(String)

    mood = Column(String)

    image_b64 = Column(String)

    likes = Column(Integer, default=0)

    timestamp = Column(DateTime, default=func.now())





class Analytics(Base):

    __tablename__ = "analytics"



    id = Column(Integer, primary_key=True, index=True)

    date = Column(Date, unique=True)

    chats_count = Column(Integer, default=0)

    likes_count = Column(Integer, default=0)

    daily_users = Column(Integer, default=0)

MODELEOF

echo "  ✓ models.py"



# ── Write auth.py ────────────────────────────────────────────────────────────

cat > backend/auth.py << 'AUTHEOF'

"""

Auth utilities — JWT creation, password hashing, token verification.

Routes (/token, /register) live in main.py.

This module is importable without a FastAPI app instance.

"""

from fastapi import Depends, HTTPException, status

from fastapi.security import OAuth2PasswordBearer

from jose import JWTError, jwt

from passlib.context import CryptContext

from datetime import datetime, timedelta

from typing import Optional

import os

from dotenv import load_dotenv

from pydantic import BaseModel



load_dotenv()



SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-prod")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")





class Token(BaseModel):

    access_token: str

    token_type: str





class User(BaseModel):

    username: str





def verify_password(plain_password: str, hashed_password: str) -> bool:

    return pwd_context.verify(plain_password, hashed_password)





def get_password_hash(password: str) -> str:

    return pwd_context.hash(password)





def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:

    to_encode = data.copy()

    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)





async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:

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

    return User(username=username)

AUTHEOF

echo "  ✓ auth.py"



# ── Write redis_client.py ────────────────────────────────────────────────────

cat > backend/redis_client.py << 'REDISEOF'

import redis

import os

import json

from dotenv import load_dotenv



load_dotenv()



REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

HAS_REDIS = False

_memory_cache = {}



try:

    r = redis.from_url(REDIS_URL)

    r.ping()

    HAS_REDIS = True

except Exception as e:

    is_missing = "localhost" in REDIS_URL

    masked = REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL

    if is_missing:

        print(f"[Redis] REDIS_URL not set, using in-memory fallback. ({e})")

    else:

        print(f"[Redis] Unavailable at {masked}: {e}. Using in-memory fallback.")





def _get(key):

    if HAS_REDIS:

        return r.get(key)

    return _memory_cache.get(key)





def _set(key, value, ex=None):

    if HAS_REDIS:

        r.set(key, value, ex=ex)

    else:

        _memory_cache[key] = value





def cache_quote_embedding(quote_id: int, embedding: list):

    _set(f"quote:{quote_id}:emb", json.dumps(embedding))





def get_cached_embedding(quote_id: int):

    raw = _get(f"quote:{quote_id}:emb")

    return json.loads(raw) if raw else None





def get_conversation(session_id: str) -> list:

    raw = _get(f"conv:{session_id}")

    return json.loads(raw) if raw else []





def save_conversation(session_id: str, conversation: list):

    _set(f"conv:{session_id}", json.dumps(conversation), ex=3600)





def cache_search(query_hash: str, results: list, ttl: int = 3600):

    _set(f"search:{query_hash}", json.dumps(results), ex=ttl)





def get_cached_search(query_hash: str):

    raw = _get(f"search:{query_hash}")

    return json.loads(raw) if raw else None





def incr_topic(topic: str):

    if HAS_REDIS:

        r.zincrby("popular_topics", 1, topic)





def get_popular_topics(top_k: int = 5, ttl: int = 3600):

    if HAS_REDIS:

        r.expire("popular_topics", ttl)

        return r.zrevrange("popular_topics", 0, top_k - 1, withscores=True)

    return []





def incr_quote_view(quote_hash: str):

    if HAS_REDIS:

        r.zincrby("popular_quotes", 1, quote_hash)





def get_popular_quotes(top_k: int = 5):

    if HAS_REDIS:

        r.expire("popular_quotes", 3600)

        return r.zrevrange("popular_quotes", 0, top_k - 1, withscores=True)

    return []

REDISEOF

echo "  ✓ redis_client.py"



# ── Write embeddings.py ──────────────────────────────────────────────────────

cat > backend/embeddings.py << 'EMBEOF'

import numpy as np

import threading

import logging

import hashlib



logger = logging.getLogger(__name__)



HAS_MODEL = False

model = None

_model_lock = threading.Lock()





def load_embedding_model():

    def _load():

        global model, HAS_MODEL

        try:

            from sentence_transformers import SentenceTransformer

            logger.info("Loading sentence-transformer model (background)...")

            _model = SentenceTransformer("paraphrase-MiniLM-L6-v2", device="cpu")

            with _model_lock:

                model = _model

                HAS_MODEL = True

            logger.info("Sentence-transformer loaded — semantic search active.")

        except Exception as e:

            logger.warning(f"Sentence-transformer unavailable: {e}. Using deterministic fallback.")

            with _model_lock:

                HAS_MODEL = False



    t = threading.Thread(target=_load, daemon=True)

    t.start()





load_embedding_model()





def embed_text(text: str) -> list:

    with _model_lock:

        m = model

        has = HAS_MODEL

    if has and m is not None:

        try:

            return m.encode(text).tolist()

        except Exception as e:

            logger.error(f"Embedding error: {e}")

    # Deterministic fallback — same text always gets same vector

    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)

    rng = np.random.default_rng(seed)

    return rng.uniform(-1, 1, 384).tolist()





def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:

    na, nb = np.linalg.norm(a), np.linalg.norm(b)

    if na == 0 or nb == 0:

        return 0.0

    return float(np.dot(a, b) / (na * nb))

EMBEOF

echo "  ✓ embeddings.py"



# ── Write generation.py ──────────────────────────────────────────────────────

cat > backend/generation.py << 'GENEOF'

import os

import random

import requests

import logging

import threading

from mtranslate import translate



logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)



HAS_GENERATOR = False

generator = None

_gen_lock = threading.Lock()





def load_model():

    def _load():

        global generator, HAS_GENERATOR

        try:

            from transformers import pipeline as hf_pipeline

            logger.info("Loading text-generation model (background)...")

            _gen = hf_pipeline("text-generation", model="distilgpt2", device=-1)

            with _gen_lock:

                generator = _gen

                HAS_GENERATOR = True

            logger.info("Text-generation model loaded successfully.")

        except ImportError as e:

            logger.warning(f"transformers.pipeline not available: {e}. Using rule-based fallback.")

            with _gen_lock:

                HAS_GENERATOR = False

        except Exception as e:

            logger.warning(f"Text-generation model failed to load: {e}. Using rule-based fallback.")

            with _gen_lock:

                HAS_GENERATOR = False



    t = threading.Thread(target=_load, daemon=True)

    t.start()





load_model()





def fetch_open_source_quote(mood: str = "") -> dict:

    try:

        resp = requests.get("https://zenquotes.io/api/random", timeout=3)

        if resp.status_code == 200:

            data = resp.json()[0]

            return {"quote": data["q"], "author": data["a"]}

    except Exception:

        pass

    try:

        tag_map = {

            "inspiring": "inspirational", "calm": "happiness",

            "energetic": "motivational", "philosophical": "wisdom",

            "stoic": "stoicism", "zen": "zen",

        }

        tag = tag_map.get(mood.lower(), "")

        url = f"https://api.quotable.io/random{f'?tags={tag}' if tag else ''}"

        resp = requests.get(url, timeout=3)

        if resp.status_code == 200:

            data = resp.json()

            return {"quote": data["content"], "author": data["author"]}

    except Exception:

        pass

    return None





def generate_quote(prompt: str, mood: str = "", max_length: int = 60) -> str:

    os_quote = fetch_open_source_quote(mood)

    if os_quote and random.random() < 0.5:

        return f'"{os_quote["quote"]}" - {os_quote["author"]}'



    with _gen_lock:

        has = HAS_GENERATOR

        gen = generator



    if not has or gen is None:

        fallbacks = [

            "The journey of a thousand miles begins with a single step. - Lao Tzu",

            "In the middle of difficulty lies opportunity. - Albert Einstein",

            "It always seems impossible until it's done. - Nelson Mandela",

            "The only way to do great work is to love what you do. - Steve Jobs",

            "Believe you can and you're halfway there. - Theodore Roosevelt",

        ]

        return random.choice(fallbacks)



    base_prompt = f"Create a profound and original quote about '{prompt}' in a {mood or 'thought-provoking'} style:"

    try:

        result = gen(

            base_prompt, max_new_tokens=max_length, num_return_sequences=1,

            do_sample=True, temperature=0.9, top_p=0.95,

            pad_token_id=gen.tokenizer.eos_token_id,

        )

        text = result[0]["generated_text"].replace(base_prompt, "").strip()

        if '"' in text:

            text = text.split('"')[1]

        return text or "To find the universal, look within the particular."

    except Exception as e:

        logger.error(f"Quote generation error: {e}")

        return "The seed of an idea is a universe in waiting."





def generate_response(prompt: str, history: list = None, mood: str = "", max_length: int = 150, lang: str = "en") -> str:

    logger.info(f"generate_response: '{prompt[:60]}' (lang={lang})")

    if not prompt or not isinstance(prompt, str):

        return "I am listening, seeker. Your silence is profound."



    input_text = prompt

    if lang == "hi":

        try:

            input_text = translate(prompt, "en", "auto")

        except Exception as e:

            logger.error(f"Translation error: {e}")



    msg = input_text.lower().strip()

    quote_keywords = ["quote", "wisdom", "inspiration", "inspire", "saying", "motto", "thought", "vichar", "suvichar"]

    visual_keywords = ["visual", "image", "picture", "art", "draw", "paint", "canvas", "background", "chitra", "photo"]



    if any(w in msg for w in visual_keywords):

        resp = "I can create a visual for you. Use the '🎨 Visual' button on any of my messages, or head to the Studio page."

        if lang == "hi":

            try: resp = translate(resp, "hi", "en")

            except Exception: pass

        return resp



    if any(w in msg for w in quote_keywords):

        topic = input_text

        for kw in quote_keywords + ["about", "in hindi"]:

            topic = topic.replace(kw, "")

        topic = topic.strip() or "life"

        detected_mood = mood or "thought-provoking"

        for m in ["stoic", "zen", "cyberpunk", "philosophical", "calm", "energetic", "inspiring", "melancholic"]:

            if m in msg:

                detected_mood = m

                break

        quote = generate_quote(topic, mood=detected_mood)

        if lang == "hi":

            try: return translate(quote, "hi", "en")

            except Exception as e: logger.error(f"Quote translation error: {e}")

        return quote



    responses = {

        "hello": "Greetings, seeker of wisdom. How may I inspire you today?",

        "hi": "Hello. I am LEVI, your artistic companion. What's on your mind?",

        "who are you": "I am LEVI, an AI muse designed to spark creativity and offer philosophical insights.",

        "how are you": "I am reflecting on the vast beauty of the digital cosmos. And you?",

        "help": "I can generate quotes, create artistic visuals, or discuss deeper meanings. Try 'give me wisdom' or 'inspire me'.",

    }

    if msg in responses:

        resp = responses[msg]

        if lang == "hi":

            try: resp = translate(resp, "hi", "en")

            except Exception: pass

        return resp



    with _gen_lock:

        has = HAS_GENERATOR

        gen = generator



    if not has or gen is None:

        resp = "I am reflecting on the deeper patterns of the universe. Ask me for 'wisdom' or a specific mood like Stoic or Cyberpunk."

        if lang == "hi":

            try: resp = translate(resp, "hi", "en")

            except Exception: pass

        return resp



    try:

        context = "LEVI is a wise, creative, and concise AI companion.\n"

        if history:

            for entry in history[-2:]:

                u, b = entry.get("user", ""), entry.get("bot", "")

                if u and b:

                    context += f"User: {u}\nLEVI: {b}\n"

        context += f"User: {input_text}\nLEVI:"

        result = gen(context, max_new_tokens=60, num_return_sequences=1, do_sample=True,

                     temperature=0.8, pad_token_id=gen.tokenizer.eos_token_id)

        response = result[0]["generated_text"].split("LEVI:")[-1].split("User:")[0].strip()

        if not response:

            response = "The silence between us is filled with potential. What shall we explore?"

        if lang == "hi":

            try: response = translate(response, "hi", "en")

            except Exception: pass

        return response

    except Exception as e:

        logger.error(f"Generation error: {e}")

        return "A momentary lapse in the cosmic connection. Ask again, and let us realign the stars."

GENEOF

echo "  ✓ generation.py"



# ── Write main.py ────────────────────────────────────────────────────────────

cat > backend/main.py << 'MAINEOF'

from fastapi import FastAPI, Depends, HTTPException, status, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from pydantic import BaseModel

from jose import JWTError, jwt

from passlib.context import CryptContext

from datetime import datetime, timedelta, date

from slowapi import Limiter

from slowapi.util import get_remote_address

from slowapi.errors import RateLimitExceeded

from slowapi import _rate_limit_exceeded_handler

import os

import logging

import requests

from dotenv import load_dotenv



load_dotenv()



logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)



try:

    from backend.db import SessionLocal, engine, get_db, DATABASE_URL

    from backend.models import Quote, Analytics, FeedItem, Base

    from backend.embeddings import embed_text, cosine_sim, HAS_MODEL

    from backend.redis_client import get_cached_search, cache_search, get_conversation, save_conversation, HAS_REDIS, REDIS_URL

    from backend.generation import generate_quote, generate_response

    from backend.image_gen import generate_quote_image

except ImportError:

    from db import SessionLocal, engine, get_db, DATABASE_URL

    from models import Quote, Analytics, FeedItem, Base

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

users_db = {}





def verify_password(plain_password, hashed_password):

    return pwd_context.verify(plain_password, hashed_password)





def get_password_hash(password):

    return pwd_context.hash(password)





def create_access_token(data: dict, expires_delta: timedelta = None):

    to_encode = data.copy()

    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)





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

async def chat(request: Request, msg: ChatMessage, db: Session = Depends(get_db)):

    logger.info(f"Chat [{msg.session_id}]: '{msg.message[:60]}'")

    today = date.today()

    analytics = db.query(Analytics).filter(Analytics.date == today).first()

    if not analytics:

        analytics = Analytics(date=today, chats_count=1)

        db.add(analytics)

    else:

        analytics.chats_count = (analytics.chats_count or 0) + 1

    db.commit()

    history = get_conversation(msg.session_id)

    bot_response = generate_response(msg.message, history=history, mood="", lang=msg.lang or "en")

    history.append({"user": msg.message, "bot": bot_response})

    save_conversation(msg.session_id, history)

    return {"response": bot_response}





@app.post("/register", response_model=Token)

async def register(user_in: UserIn):

    if user_in.username in users_db:

        raise HTTPException(status_code=400, detail="Username already registered")

    users_db[user_in.username] = {

        "username": user_in.username,

        "hashed_password": get_password_hash(user_in.password),

    }

    token = create_access_token(data={"sub": user_in.username},

                                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    return {"access_token": token, "token_type": "bearer"}





@app.post("/token", response_model=Token)

async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):

    user = users_db.get(form_data.username)

    if not user or not verify_password(form_data.password, user["hashed_password"]):

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = create_access_token(data={"sub": user["username"]},

                                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    return {"access_token": token, "token_type": "bearer"}





if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

MAINEOF

echo "  ✓ main.py"



# ── Write frontend/js/api.js ─────────────────────────────────────────────────

cat > frontend/js/api.js << 'APIEOF'

if (window.location.protocol === 'file:') {

  console.error('[LEVI] Website cannot run via file:// protocol. Please use a local server.');

  alert('LEVI Error: Run "python run_app.py" and visit http://localhost:8080');

}



let hostname = window.location.hostname;

if (hostname === '0.0.0.0') hostname = '127.0.0.1';



const isLocalDev = window.location.port === '8080' || hostname === 'localhost' || hostname === '127.0.0.1';

export const API_BASE = isLocalDev

  ? `${window.location.protocol}//${hostname}:8000`

  : window.location.origin + '/api';



console.log(`[LEVI] API Base: ${API_BASE}`);



async function apiFetch(endpoint, options = {}) {

  const url = `${API_BASE}${endpoint}`;

  const finalOptions = { headers: { 'Content-Type': 'application/json' }, ...options };

  if (options.body && typeof options.body !== 'string') {

    finalOptions.body = JSON.stringify(options.body);

  }

  try {

    const res = await fetch(url, finalOptions);

    if (!res.ok) {

      const errorData = await res.json().catch(() => ({}));

      throw new Error(errorData.detail || `API error: ${res.status}`);

    }

    return await res.json();

  } catch (error) {

    console.error(`[LEVI] Fetch error for ${endpoint}:`, error);

    throw error;

  }

}



export async function chat(message, session = 'user1') {

  const lang = localStorage.getItem('levi_lang') || 'en';

  return apiFetch('/chat', { method: 'POST', body: { session_id: session, message, lang } });

}

export async function login(username, password) {

  const formData = new FormData();

  formData.append('username', username);

  formData.append('password', password);

  const res = await fetch(`${API_BASE}/token`, { method: 'POST', body: formData });

  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Login failed: ${res.status}`); }

  return res.json();

}

export async function register(username, password) {

  return apiFetch('/register', { method: 'POST', body: { username, password } });

}

export async function getProfile(token) {

  return apiFetch('/users/me', { headers: { Authorization: `Bearer ${token}` } });

}

export async function searchQuotes(text, filters = {}) {

  return apiFetch('/search_quotes', { method: 'POST', body: { text, ...filters, top_k: 5 } });

}

export async function generateQuote(topic, mood = '') {

  return apiFetch('/generate', { method: 'POST', body: { text: topic, mood } });

}

export async function getDailyQuote() { return apiFetch('/daily_quote'); }

export async function getAnalytics() { return apiFetch('/analytics'); }

export async function generateQuoteImage(text, author = 'Unknown', mood = 'neutral', options = {}) {

  return apiFetch('/generate_image', { method: 'POST', body: { text, author, mood, ...options } });

}

export async function getFeed(limit = 20) { return apiFetch(`/feed?limit=${limit}`); }

export async function likeItem(type, id) { return apiFetch(`/like/${type}/${id}`, { method: 'POST' }); }



window.api = { chat, login, register, getProfile, searchQuotes, generateQuote, getDailyQuote, generateQuoteImage, getAnalytics, getFeed, likeItem };

APIEOF

echo "  ✓ frontend/js/api.js"



# ── Verify Python files parse ────────────────────────────────────────────────

echo ""

echo "Verifying Python syntax..."

for f in backend/main.py backend/models.py backend/auth.py backend/embeddings.py backend/generation.py backend/redis_client.py; do

  python3 -c "import ast; ast.parse(open('$f').read())" && echo "  ✓ $f" || echo "  ✗ SYNTAX ERROR: $f"

done



# ── Git add, commit, push ────────────────────────────────────────────────────
echo ""
echo "Pushing to GitHub..."
git add \
  main.py \
  backend/main.py \
  backend/models.py \
  backend/auth.py \
  backend/embeddings.py \
  backend/generation.py \
  backend/redis_client.py \
  backend/requirements.txt \
  frontend/js/api.js

git commit -m "fix: complete backend overhaul — all files synced

- main.py (root): add entrypoint proxy for Render/Vercel
- models.py: add FeedItem, Analytics, UniqueConstraint
- main.py (backend): remove module-level pwd_context.hash, async image gen
- requirements.txt: pin transformers<5.0, bcrypt<5.0
- generation.py: lazy pipeline import, safe fallback
- embeddings.py: thread-safe, deterministic fallback
- auth.py: remove broken @app decorator
- redis_client.py: export HAS_REDIS, REDIS_URL
- frontend/js/api.js: remove duplicate getAnalytics export"



git push origin main



echo ""

echo "========================================"

echo "  All files pushed to GitHub!"

echo "  Render will auto-deploy now."

echo ""

echo "  Expected in logs:"

echo "  ✅ Redis connected"

echo "  ✅ Database tables ready"

echo "  ✅ Application startup complete"

echo "  ✅ Your service is live"

echo "========================================"