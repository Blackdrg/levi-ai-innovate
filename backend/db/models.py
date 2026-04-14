from typing import Any, Dict
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB
from backend.db.postgres import Base
from datetime import datetime, timezone
import os

class UserProfile(Base):
    """
    Sovereign User Profile (Tier 4 Memory - Traits & Preferences).
    Centralized store for highly distilled identity archetypes.
    """
    __tablename__ = "user_profiles"
    __tenant_scoped__ = True # Flag for RLS enforcement

    user_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True) # Domain/Org partitioning
    role = Column(String, default="user") # user, admin, auditor
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
    tenant_id = Column(String, index=True)
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
    tenant_id = Column(String, index=True)
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
    tenant_id = Column(String, index=True)
    intent = Column(String)
    status = Column(String)
    token_count = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CustomAgent(Base):
    """
    User-defined agent archetypes (v14.0.0-Autonomous-SOVEREIGN).
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
    Standard audit ledger for HIPAA/GDPR compliance.
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
    prev_signature = Column(String) # Cryptographic chain link
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def calculate_signature(prev_sig: str, data: str) -> str:
        """
        v14.0.0-Autonomous-SOVEREIGN: Cryptographic chaining.
        HMAC-SHA256(prev_sig + data)
        """
        import hmac
        import hashlib
        secret = os.getenv("AUDIT_CHAIN_SECRET", "levi_ai_genesis_key")
        msg = f"{prev_sig}:{data}".encode()
        return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()

class AuditLog(Base):
    """
    Sovereign v14.0.0-Autonomous-SOVEREIGN: Immutable High-Fidelity Audit Ledger.
    Partitioned by month for long-term scalability and performance.
    """
    __tablename__ = "audit_log"
    __table_args__ = (
        {'postgresql_partition_by': 'RANGE (created_at)'},
    )

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False, index=True) # RBAC, KMS, AGENT, GDPR, HITL
    user_id = Column(String, index=True)
    resource_id = Column(String, index=True)
    action = Column(String, nullable=False)
    status = Column(String, default="success")
    metadata_json = Column(JSON, default={})
    
    # Cryptographic Integrity
    checksum = Column(String, nullable=False) # SHA-256(row_data + prev_checksum)
    
    created_at = Column(DateTime, primary_key=True, default=lambda: datetime.now(timezone.utc))

    @classmethod
    def calculate_checksum(cls, prev_hash: str, row_data: dict) -> str:
        """
        Sovereign v15.0: HMAC-Chained Integrity Ledger.
        Formula: hash_n = HMAC_SHA256(secret, data_n + hash_{n-1})
        """
        import hmac
        import hashlib
        import json
        
        secret = os.getenv("AUDIT_CHAIN_SECRET", "levi_ai_genesis_key_v15")
        
        # Consistent serialization of row data
        data_str = json.dumps(row_data, sort_keys=True)
        
        # Combine data with previous hash
        combined = f"{data_str}|{prev_hash}".encode()
        
        return hmac.new(secret.encode(), combined, hashlib.sha256).hexdigest()

    @classmethod
    async def verify_chain(cls, session: Any, limit: int = 100) -> Dict[str, Any]:
        """
        Sovereign v15.0: Cryptographic Chain Verification.
        Traverses the ledger and verifies the HMAC chain integrity.
        """
        from sqlalchemy import select
        query = select(cls).order_by(cls.created_at.desc()).limit(limit)
        result = await session.execute(query)
        logs = result.scalars().all()
        
        if not logs:
            return {"status": "empty", "valid": True}
        
        # We verify in chronological order
        logs_asc = logs[::-1]
        prev_hash = "GENESIS" # In production, this would be fetched from the last verified block
        
        violations = []
        for log in logs_asc:
            row_data = {
                "event_type": log.event_type,
                "user_id": log.user_id,
                "resource_id": log.resource_id,
                "action": log.action,
                "status": log.status,
                "metadata": log.metadata_json
            }
            expected_hash = cls.calculate_checksum(prev_hash, row_data)
            if expected_hash != log.checksum:
                violations.append({
                    "id": log.id,
                    "expected": expected_hash,
                    "actual": log.checksum,
                    "timestamp": log.created_at.isoformat()
                })
            prev_hash = log.checksum
            
        return {
            "status": "verified" if not violations else "compromised",
            "valid": len(violations) == 0,
            "violations": violations,
            "record_count": len(logs)
        }

class MissionSchedule(Base):
    """
    Recurring mission manifests.
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

class UserFact(Base):
    """
    Episodic memory and learned facts.
    Stored in local Postgres persistent layer.
    """
    __tablename__ = "user_facts"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    tenant_id = Column(String, index=True)
    fact = Column(Text, nullable=False)
    category = Column(String, default="general")
    importance = Column(Float, default=0.5)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=False)

    profile = relationship("UserProfile")

class Goal(Base):
    """
    Sovereign v15.0: Persistent Long-term Objective.
    Goals are the "Directives" that survive sessions and drive autonomous mission spawning.
    Supports recursive decomposition via parent_goal_id.
    """
    __tablename__ = "goals"

    goal_id = Column(String, primary_key=True, index=True)
    parent_goal_id = Column(String, ForeignKey("goals.goal_id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    tenant_id = Column(String, index=True)
    
    objective = Column(Text, nullable=False)
    status = Column(String, default="active") # active, achieved, stalled, canceled
    priority = Column(Float, default=1.0) # 1.0 (Normal) to 10.0 (Critical)
    progress = Column(Float, default=0.0) # 0.0 - 1.0
    
    metadata_json = Column(JSON, default={}) # Strategy, heuristics, constraints
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    sub_goals = relationship("Goal", backref=backref("parent_goal", remote_side=[goal_id]))
    missions = relationship("Mission", back_populates="goal")

class Mission(Base):
    """
    Distributed Mission Ledger.
    Records interaction history for local-first cognitive missions.
    """
    __tablename__ = "missions"

    mission_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    goal_id = Column(String, ForeignKey("goals.goal_id"), nullable=True, index=True)
    tenant_id = Column(String, index=True)
    objective = Column(String, nullable=False)
    intent_type = Column(String)
    status = Column(String, default="pending")
    fidelity_score = Column(Float, default=0.0)
    payload = Column(JSON) # Stores checkpoint and DAG state (v14.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    goal = relationship("Goal", back_populates="missions")
    aborted_record = relationship("AbortedMission", back_populates="mission", uselist=False)
    messages = relationship("Message", back_populates="mission", cascade="all, delete-orphan")

class Message(Base):
    """
    Individual messages within a mission.
    """
    __tablename__ = "mission_messages"

    id = Column(Integer, primary_key=True)
    mission_id = Column(String, ForeignKey("missions.mission_id"), index=True)
    role = Column(String) # user, bot, system
    content = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    mission = relationship("Mission", back_populates="messages")

class CognitiveUsage(Base):
    """
    Mission Resource Ledger (v14.0.0-Autonomous-SOVEREIGN).
    Tracks token consumption and resource costs for local-first missions.
    """
    __tablename__ = "cognitive_usage"

    id = Column(Integer, primary_key=True)
    mission_id = Column(String, ForeignKey("missions.mission_id"), index=True)
    user_id = Column(String, index=True)
    agent = Column(String)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    cu_cost = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    mission = relationship("Mission")

class CreationJob(Base):
    """
    Creation Ledger v14.0.0-Autonomous-SOVEREIGN.
    Replaces Firestore 'jobs' with resident SQL persistence for Studio/Gallery.
    """
    __tablename__ = "creation_jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, index=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), index=True)
    tenant_id = Column(String, index=True)
    objective = Column(Text, nullable=False)
    status = Column(String, default="pending") # pending, processing, completed, failed
    result_url = Column(String) # Local artifact path
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)

    profile = relationship("UserProfile")

class TrainingPattern(Base):
    """
    Sovereign v14.0.0-Autonomous-SOVEREIGN Learning Corpus.
    Captures high-fidelity mission results for future LoRA fine-tuning.
    """
    __tablename__ = "training_corpus"

    id = Column(Integer, primary_key=True)
    mission_id = Column(String, unique=True, index=True)
    query = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    fidelity_score = Column(Float, nullable=False)
    is_trained = Column(Boolean, default=False) # Flag for LoRA promotion
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class GraduatedRule(Base):
    """
    Sovereign v15.0 Evolved Deterministic Rules.
    High-fidelity patterns promoted to hard-coded rules for the fast-path.
    """
    __tablename__ = "graduated_rules"

    id = Column(Integer, primary_key=True)
    task_pattern = Column(Text, unique=True, index=True, nullable=False)
    result_data = Column(JSON, nullable=False)
    fidelity_score = Column(Float, nullable=False)
    uses_count = Column(Integer, default=0)
    
    # 🧪 Phase 3: Shadow Auditing & Drift
    shadow_audit_count = Column(Integer, default=0)
    divergence_count = Column(Integer, default=0) # Consecutive shadow failures
    drift_score = Column(Float, default=0.0) 
    
    is_stable = Column(Boolean, default=False)
    is_quarantined = Column(Boolean, default=False)
    
    last_drift_check = Column(DateTime)
    last_validated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class FragilityIndex(Base):
    """
    Sovereign v14.1 Cognitive Fragility Tracker.
    Monitors failure rates across intent domains to drive deep reasoning.
    """
    __tablename__ = "fragility_index"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    domain = Column(String, index=True) # e.g. "code", "search", "creative"
    failure_count = Column(Integer, default=0)
    success_streak = Column(Integer, default=0)
    weighted_fidelity = Column(Float, default=1.0)
    fragility_score = Column(Float, default=0.0) # Calculated domain fragility
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CriticCalibration(Base):
    """
    Sovereign v14.0 Bias Correction Ledger.
    Tracks primary and shadow critic scores to identify calibration drift.
    """
    __tablename__ = "critic_calibration"

    id = Column(Integer, primary_key=True)
    mission_id = Column(String, index=True)
    user_id = Column(String, index=True) # Personalized Bias Tracking
    primary_score = Column(Float, nullable=False)
    shadow_score = Column(Float, nullable=False)
    human_score = Column(Float, nullable=True) # Populated via HITL review
    divergence = Column(Float, nullable=False) # abs(primary - shadow)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UserCalibration(Base):
    """
    Sovereign v14.0.0 Phase 8.
    Stores the calculated scoring offset for each user to correct CriticAgent bias.
    """
    __tablename__ = "user_calibration"

    user_id = Column(String, primary_key=True)
    bias_offset = Column(Float, default=0.0)
    samples_analyzed = Column(Integer, default=0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class BenchmarkLedger(Base):
    """
    Sovereign Benchmark Ledger v14.0.
    Stores high-fidelity performance metrics (p50/p95/p99) across models and context lengths.
    """
    __tablename__ = "benchmark_ledger"

    id = Column(Integer, primary_key=True)
    model = Column(String, index=True)
    tier = Column(String, index=True) # L1, L2, L3, L4
    context_length = Column(Integer, index=True) # 512, 1024, 2048, 4096
    p50_latency_ms = Column(Float)
    p95_latency_ms = Column(Float)
    p99_latency_ms = Column(Float)
    tps_p50 = Column(Float) # Tokens Per Second
    samples = Column(Integer, default=100)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AbortedMission(Base):
    """
    Sovereign v14.0.0-Autonomous Resilience Layer.
    Persists frozen DAG state and execution wave for transient failure replay.
    """
    __tablename__ = "missions_aborted"

    id = Column(Integer, primary_key=True)
    mission_id = Column(String, ForeignKey("missions.mission_id"), unique=True, index=True)
    user_id = Column(String, index=True)
    
    frozen_dag = Column(JSON) # Full serialized Graph object
    wave_index = Column(Integer, default=0) # Last successful wave
    error_node_id = Column(String)
    
    payload = Column(JSON) # Input context
    aborted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    mission = relationship("Mission", back_populates="aborted_record")

class UserCredit(Base):
    """
    Sovereign v14.1 Monetization Layer.
    Tracks user cognitive credits and subscription tier.
    """
    __tablename__ = "user_credits"

    user_id = Column(String, primary_key=True, index=True)
    credits_remaining = Column(Float, default=100.0) # Free credits baseline
    tier = Column(String, default="seeker") # seeker, pro, creator
    next_reset_at = Column(DateTime)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class BenchmarkingLog(Base):
    """
    Sovereign Benchmarking Ledger (Phase 1: Measurement).
    Records comparative performance against other AI frameworks.
    """
    __tablename__ = "benchmarking_logs"

    id = Column(Integer, primary_key=True)
    task_name = Column(String, index=True) # e.g., "market_research", "code_gen"
    competitor = Column(String, index=True) # e.g., "LangChain", "CrewAI", "LEVI-AI"
    latency_seconds = Column(Float)
    accuracy_score = Column(Float)
    cost_estimate = Column(Float)
    hardware_specs = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EvolutionMetric(Base):
    """
    Sovereign Self-Monitoring Ledger (Phase 2: Self-Mutation).
    Continuously tracks system accuracy, hallucination, and efficiency.
    """
    __tablename__ = "evolution_metrics"

    id = Column(Integer, primary_key=True)
    mission_id = Column(String, ForeignKey("missions.mission_id"), index=True)
    accuracy_score = Column(Float)
    hallucination_rate = Column(Float)
    reasoning_score = Column(Float)
    latency_ms = Column(Float)
    cost_usd = Column(Float)
    status = Column(String)
    metadata_json = Column(JSON, default={})
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class FailurePattern(Base):
    """
    Sovereign Failure Intelligence (Phase 2: Analyzer).
    Stores root cause analysis and fix suggestions for recurrent failures.
    """
    __tablename__ = "failure_patterns"

    id = Column(Integer, primary_key=True)
    failure_type = Column(String, index=True) # e.g., "agent_timeout", "hallucination"
    root_cause = Column(Text)
    fix_suggestion = Column(Text)
    occurrence_count = Column(Integer, default=1)
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SuccessPattern(Base):
    """
    Sovereign Success Intelligence (Phase 2: Learner).
    Stores proven agent high-fidelity sequences and parameters.
    """
    __tablename__ = "success_patterns"

    id = Column(Integer, primary_key=True)
    objective_pattern = Column(Text, unique=True, index=True)
    agent_sequence = Column(JSON)
    parameters = Column(JSON)
    fidelity_avg = Column(Float)
    win_count = Column(Integer, default=1)
    last_used_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class MutationProposal(Base):
    """
    Sovereign Self-Mutation Ledger (Phase 2: Mutator).
    Records system-generated improvements to algorithms and strategies.
    """
    __tablename__ = "mutation_proposals"

    id = Column(Integer, primary_key=True)
    mutation_type = Column(String) # "algorithm" or "strategy"
    proposal_name = Column(String)
    logic_diff = Column(Text)
    target_metric = Column(String)
    expected_improvement = Column(Float)
    status = Column(String, default="proposed") # proposed, testing, adopted, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DiscoveredCapability(Base):
    """
    Sovereign Emergence Ledger (Phase 2: Discovery).
    Records capabilities identified by the system that weren't explicitly designed.
    """
    __tablename__ = "discovered_capabilities"

    id = Column(Integer, primary_key=True)
    capability_name = Column(String, unique=True)
    agents_involved = Column(JSON)
    novelty_score = Column(Float)
    use_cases = Column(JSON)
    first_detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AgentPolicy(Base):
    """
    Sovereign v15.0 Policy Gradient Ledger.
    Stores optimized hyper-parameters (Temp, Top_P, Model) for agents.
    """
    __tablename__ = "agent_policies"

    id = Column(Integer, primary_key=True)
    agent_type = Column(String, index=True) # planner, critic, search, creator
    domain = Column(String, index=True, default="default")
    
    # Hyper-parameters
    temperature = Column(Float, default=0.7)
    top_p = Column(Float, default=0.9)
    model = Column(String, default="default")
    max_tokens = Column(Integer, default=1024)
    
    # Metadata
    fidelity_avg = Column(Float, default=0.0)
    samples = Column(Integer, default=0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
