from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, JSON, PickleType, UniqueConstraint
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

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    author = Column(String)
    topic = Column(String)
    mood = Column(String)
    
    if HAS_PGVECTOR and "postgresql" in DATABASE_URL:
        embedding = Column(VECTOR(384))
    else:
        # Fallback for SQLite
        embedding = Column(PickleType)
        
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('text', name='_quote_text_uc'),)

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

class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    chats_count = Column(Integer, default=0)
    popular_topics = Column(JSON)
    likes_count = Column(Integer, default=0)
    daily_users = Column(Integer, default=0)

class FeedItem(Base):
    __tablename__ = "feed"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    author = Column(String)
    mood = Column(String)
    image_b64 = Column(String)
    likes = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
