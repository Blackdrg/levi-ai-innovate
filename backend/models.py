# pyright: reportMissingImports=false
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, JSON, PickleType  # type: ignore
from sqlalchemy.orm import Mapped, mapped_column, relationship  # type: ignore
import datetime
from datetime import datetime as dt_datetime, date as dt_date
try:
    from pgvector.sqlalchemy import Vector as VECTOR  # type: ignore
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

try:
    from backend.db import Base, DATABASE_URL  # type: ignore
except ImportError:
    from db import Base, DATABASE_URL  # type: ignore
from sqlalchemy.sql import func  # type: ignore
from typing import List, Optional


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]         = mapped_column(primary_key=True, index=True)
    text: Mapped[str]       = mapped_column(nullable=False)
    author: Mapped[Optional[str]]     = mapped_column()
    topic: Mapped[Optional[str]]      = mapped_column()
    mood: Mapped[Optional[str]]       = mapped_column()
    likes: Mapped[int]      = mapped_column(default=0)
    created_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    if HAS_PGVECTOR and "postgresql" in DATABASE_URL:
        embedding = mapped_column(VECTOR(384))
    else:
        # Fallback for SQLite/Local; PickleType stores the vector as a blob.
        # This prevents schema divergence by keeping the column name and purpose identical.
        embedding = mapped_column(PickleType)


class Users(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]                 = mapped_column(primary_key=True, index=True)
    username: Mapped[str]           = mapped_column(unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]]    = mapped_column(unique=True, index=True, nullable=True)
    password_hash: Mapped[str]      = mapped_column(nullable=False)
    created_at: Mapped[dt_datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    # ── Auth & Verification ──────────────────
    is_verified: Mapped[int]        = mapped_column(default=0)          # 0=false, 1=true (using Integer for SQLite compatibility if needed, or Boolean)
    verification_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    # Token expiry — tokens older than 24 h are rejected (fixes: plain UUID tokens with no expiry)
    verification_token_expires_at: Mapped[Optional[dt_datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Subscription & Credits ──────────────────
    tier: Mapped[str]               = mapped_column(default="free")      # free / pro / creator
    credits: Mapped[int]            = mapped_column(default=10)         # Free tier starts with 10
    razorpay_customer_id: Mapped[Optional[str]] = mapped_column(nullable=True)       # Set after first payment

    # ── Personalization ─────────────────────────
    liked_topics: Mapped[list]      = mapped_column(JSON, default=list)          # ["philosophy","success"]
    mood_history: Mapped[list]      = mapped_column(JSON, default=list)          # ["zen","stoic"]
    share_count: Mapped[int]        = mapped_column(default=0)          # Viral reward loop progress
    bonus_credits: Mapped[int]      = mapped_column(default=0)
    
    # ── Password Reset ──────────────────────────
    reset_password_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    reset_password_token_expires_at: Mapped[Optional[dt_datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]        = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int]   = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str]   = mapped_column(nullable=False)
    response: Mapped[str]  = mapped_column(nullable=False)
    timestamp: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserMemory(Base):
    __tablename__ = "user_memory"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]               = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int]          = mapped_column(ForeignKey("users.id"), unique=True)
    mood_history: Mapped[list]    = mapped_column(JSON, default=list)
    liked_topics: Mapped[list]    = mapped_column(JSON, default=list)
    interaction_count: Mapped[int] = mapped_column(default=0)
    structured_memory: Mapped[dict] = mapped_column(JSON, default=dict)  # {"entities": {}, "relations": []}
    last_active: Mapped[dt_datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeedItem(Base):
    __tablename__ = "feed_items"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]         = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]]    = mapped_column(ForeignKey("users.id"), nullable=True) # Associated creator
    text: Mapped[Optional[str]]       = mapped_column()
    author: Mapped[Optional[str]]     = mapped_column()
    mood: Mapped[Optional[str]]       = mapped_column()
    image_b64: Mapped[Optional[str]]  = mapped_column()
    image_url: Mapped[Optional[str]]  = mapped_column(nullable=True)   # S3 URL when available
    video_url: Mapped[Optional[str]]  = mapped_column(nullable=True)   # S3 video URL
    likes: Mapped[int]      = mapped_column(default=0)
    timestamp: Mapped[dt_datetime]  = mapped_column(DateTime, default=func.now(), index=True)

    # Composite index for user feed browsing
    __table_args__ = (
        # Note: SQLAlchemy index on multiple columns
        # Index('ix_feed_items_user_timestamp', 'user_id', 'timestamp'),
        {'extend_existing': True}
    )


class Analytics(Base):
    __tablename__ = "analytics"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]          = mapped_column(primary_key=True, index=True)
    date: Mapped[dt_date]    = mapped_column(Date, unique=True)
    chats_count: Mapped[int] = mapped_column(default=0)
    likes_count: Mapped[int] = mapped_column(default=0)
    daily_users: Mapped[int] = mapped_column(default=0)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]       = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int]  = mapped_column(ForeignKey("users.id"))
    endpoint: Mapped[str] = mapped_column(nullable=False)
    p256dh: Mapped[str]   = mapped_column(nullable=False)
    auth: Mapped[str]     = mapped_column(nullable=False)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]             = mapped_column(primary_key=True, index=True)
    payment_id: Mapped[str]     = mapped_column(String(100), unique=True, index=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_id: Mapped[Optional[int]]  = mapped_column(ForeignKey("users.id"), nullable=True)
    amount: Mapped[float]       = mapped_column(default=0.0)
    currency: Mapped[str]       = mapped_column(String(10), default="INR")
    status: Mapped[str]         = mapped_column(String(20), default="captured")
    timestamp: Mapped[dt_datetime] = mapped_column(DateTime, default=func.now())


class Persona(Base):
    __tablename__ = "personas"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True) # None = Admin built-in
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    system_prompt: Mapped[str] = mapped_column(String(2000), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_public: Mapped[bool] = mapped_column(default=True)
    likes: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[dt_datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())