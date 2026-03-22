"""
LEVI Training Data Models
SQLAlchemy ORM classes for the AI self-learning system.
Add these to your Alembic migration.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

try:
    from backend.db import Base
except ImportError:
    from db import Base


class TrainingData(Base):
    """
    Every conversation turn stored for learning.
    High-rated turns (rating >= 4) feed into fine-tuning.
    """
    __tablename__ = "training_data"
    __table_args__ = {"extend_existing": True}

    id           = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    mood         = Column(String, default="philosophical")
    rating       = Column(Integer, nullable=True)       # 1-5; null = not yet rated
    session_id   = Column(String, nullable=False)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    fingerprint  = Column(String, unique=True, nullable=True)  # dedup hash
    is_exported  = Column(Boolean, default=False)       # has been included in a training job
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class PromptPerformance(Base):
    """
    Tracks which system prompt variant produces the best-rated responses.
    variant_idx maps to AdaptivePromptManager.PROMPT_VARIANTS.
    """
    __tablename__ = "prompt_performance"
    __table_args__ = {"extend_existing": True}

    id           = Column(Integer, primary_key=True, index=True)
    variant_idx  = Column(Integer, unique=True, nullable=False)
    avg_score    = Column(Float, default=3.0)
    sample_count = Column(Integer, default=0)
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class ModelVersion(Base):
    """
    Records every fine-tuned model version produced.
    Only one row has is_active=True at a time.
    """
    __tablename__ = "model_versions"
    __table_args__ = {"extend_existing": True}

    id               = Column(Integer, primary_key=True, index=True)
    job_id           = Column(String, unique=True, nullable=False)
    model_id         = Column(String, unique=True, nullable=False)  # Together AI model ID
    training_samples = Column(Integer, default=0)
    eval_score       = Column(Float, nullable=True)      # 0-1 evaluation score
    is_active        = Column(Boolean, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class TrainingJob(Base):
    """
    Tracks the lifecycle of a Together AI fine-tuning job.
    """
    __tablename__ = "training_jobs"
    __table_args__ = {"extend_existing": True}

    id               = Column(Integer, primary_key=True, index=True)
    job_id           = Column(String, unique=True, nullable=False)
    file_id          = Column(String, nullable=True)
    training_samples = Column(Integer, default=0)
    status           = Column(String, default="pending")  # pending, running, completed, failed
    error_message    = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    completed_at     = Column(DateTime(timezone=True), nullable=True)


class ResponseFeedback(Base):
    """
    Explicit thumbs-up/down or star ratings submitted by users.
    Linked to a training_data row.
    """
    __tablename__ = "response_feedback"
    __table_args__ = {"extend_existing": True}

    id              = Column(Integer, primary_key=True, index=True)
    training_data_id = Column(Integer, ForeignKey("training_data.id"), nullable=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id      = Column(String, nullable=False)
    message_hash    = Column(String, nullable=False)  # hash of the message being rated
    rating          = Column(Integer, nullable=False)  # 1-5
    feedback_type   = Column(String, default="star")   # star, thumbs, implicit
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
