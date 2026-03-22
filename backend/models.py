from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, JSON, PickleType
try:
    from sqlalchemy.dialects.postgresql import VECTOR
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

try:
    from backend.db import Base, DATABASE_URL
except ImportError:
    from db import Base, DATABASE_URL
from sqlalchemy.sql import func


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = {'extend_existing': True}

    id         = Column(Integer, primary_key=True, index=True)
    text       = Column(String, nullable=False)
    author     = Column(String)
    topic      = Column(String)
    mood       = Column(String)
    likes      = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    if HAS_PGVECTOR and "postgresql" in DATABASE_URL:
        embedding = Column(VECTOR(384))
    else:
        embedding = Column(PickleType)


class Users(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id                 = Column(Integer, primary_key=True, index=True)
    username           = Column(String, unique=True, index=True, nullable=False)
    email              = Column(String, unique=True, index=True, nullable=True)
    password_hash      = Column(String, nullable=False)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())

    # ── Subscription & Credits ──────────────────
    tier               = Column(String, default="free")      # free / pro / creator
    credits            = Column(Integer, default=10)         # Free tier starts with 10
    stripe_customer_id = Column(String, nullable=True)       # Set after first Stripe payment

    # ── Personalization ─────────────────────────
    liked_topics       = Column(JSON, default=list)          # ["philosophy","success"]
    mood_history       = Column(JSON, default=list)          # ["zen","stoic"]
    share_count        = Column(Integer, default=0)          # Viral reward loop progress
    bonus_credits      = Column(Integer, default=0)


class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = {'extend_existing': True}

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"))
    message   = Column(String, nullable=False)
    response  = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class UserMemory(Base):
    __tablename__ = "user_memory"
    __table_args__ = {'extend_existing': True}

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), unique=True)
    mood_history     = Column(JSON, default=list)
    liked_topics     = Column(JSON, default=list)
    interaction_count = Column(Integer, default=0)
    last_active      = Column(DateTime(timezone=True), server_default=func.now())


class FeedItem(Base):
    __tablename__ = "feed_items"
    __table_args__ = {'extend_existing': True}

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True) # Associated creator
    text       = Column(String)
    author     = Column(String)
    mood       = Column(String)
    image_b64  = Column(String)
    image_url  = Column(String, nullable=True)   # S3 URL when available
    video_url  = Column(String, nullable=True)   # S3 video URL
    likes      = Column(Integer, default=0)
    timestamp  = Column(DateTime, default=func.now())


class Analytics(Base):
    __tablename__ = "analytics"
    __table_args__ = {'extend_existing': True}

    id          = Column(Integer, primary_key=True, index=True)
    date        = Column(Date, unique=True)
    chats_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    daily_users = Column(Integer, default=0)