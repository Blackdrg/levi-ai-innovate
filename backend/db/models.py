from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from backend.db.postgres import Base
from datetime import datetime, timezone

class UserProfile(Base):
    """
    Sovereign User Profile (Tier 4 Memory - Traits & Preferences).
    Centralized store for highly distilled identity archetypes.
    """
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True, index=True)
    response_style = Column(String, default="balanced")
    persona_archetype = Column(String, default="philosophical")
    avg_rating = Column(Float, default=3.0)
    total_interactions = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    traits = relationship("UserTrait", back_populates="profile", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="profile", cascade="all, delete-orphan")

class UserTrait(Base):
    """
    Distilled identity traits (e.g., 'Values Stoicism', 'Risk Averse').
    """
    __tablename__ = "user_traits"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    trait = Column(String, nullable=False)
    weight = Column(Float, default=0.5)
    evidence_count = Column(Integer, default=1)
    crystallized_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    profile = relationship("UserProfile", back_populates="traits")

class UserPreference(Base):
    """
    Specific user preferences and learned behaviors.
    """
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    category = Column(String) # e.g., 'topic', 'format', 'tone'
    value = Column(String)
    resonance_score = Column(Float, default=0.5)

    profile = relationship("UserProfile", back_populates="preferences")

class MissionMetric(Base):
    """
    Performance and Cost Analytics for every Sovereign Mission.
    """
    __tablename__ = "mission_metrics"

    id = Column(Integer, primary_key=True)
    mission_id = Column(String, index=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    intent = Column(String)
    status = Column(String)
    token_count = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CustomAgent(Base):
    """
    User-defined agent archetypes (v13.0.0 No-Code Builder).
    """
    __tablename__ = "custom_agents"

    agent_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    config_json = Column(JSON) # Stores DAG/Prompt/Tools
    is_public = Column(Integer, default=0) # 0: Private, 1: Public
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class MarketplaceAgent(Base):
    """
    Official and Community agents available for installation.
    """
    __tablename__ = "marketplace_agents"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String, index=True)
    name = Column(String, nullable=False)
    creator_id = Column(String)
    description = Column(Text)
    price_units = Column(Integer, default=0)
    category = Column(String)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=5.0)
    config_json = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SystemAudit(Base):
    """
    High-fidelity audit ledger for HIPAA/GDPR compliance.
    """
    __tablename__ = "system_audit"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    action = Column(String, nullable=False)
    resource_id = Column(String) # e.g., mission_id, agent_id
    detail = Column(Text)
    ip_address = Column(String)
    user_agent = Column(String)
    signature = Column(String) # HMAC-SHA256 integrity pulse
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class MissionSchedule(Base):
    """
    Recurring mission manifests (v13.0.0 Scheduled Missions).
    """
    __tablename__ = "mission_schedules"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    name = Column(String, nullable=False)
    mission_input = Column(Text, nullable=False)
    cron_expression = Column(String) # e.g. "0 9 * * *"
    interval_seconds = Column(Integer) # e.g. 3600
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
