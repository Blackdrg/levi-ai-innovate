from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, JSON, PickleType
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
from datetime import datetime as dt_datetime, date as dt_date
try:
    from pgvector.sqlalchemy import Vector as VECTOR
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

try:
    from backend.db import Base, DATABASE_URL
except ImportError:
    from db import Base, DATABASE_URL
from sqlalchemy.sql import func
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

    # ── Subscription & Credits ──────────────────
    tier: Mapped[str]               = mapped_column(default="free")      # free / pro / creator
    credits: Mapped[int]            = mapped_column(default=10)         # Free tier starts with 10
    razorpay_customer_id: Mapped[Optional[str]] = mapped_column(nullable=True)       # Set after first payment

    # ── Personalization ─────────────────────────
    liked_topics: Mapped[list]      = mapped_column(JSON, default=list)          # ["philosophy","success"]
    mood_history: Mapped[list]      = mapped_column(JSON, default=list)          # ["zen","stoic"]
    share_count: Mapped[int]        = mapped_column(default=0)          # Viral reward loop progress
    bonus_credits: Mapped[int]      = mapped_column(default=0)


class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int]        = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int]   = mapped_column(ForeignKey("users.id"))
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
    timestamp: Mapped[dt_datetime]  = mapped_column(DateTime, default=func.now())


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