-- LeviBrain v8: High-Fidelity Postgres Schema
-- Unified persistence for the Cognitive Monolith

-- 1. Identity & Profile Layer
CREATE TABLE IF NOT EXISTS user_profiles (
    uid VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    subscription_tier VARCHAR(50) DEFAULT 'free',
    fidelity_preference FLOAT DEFAULT 0.85,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Mission & Orchestration Layer
CREATE TABLE IF NOT EXISTS missions (
    mission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) REFERENCES user_profiles(uid),
    objective TEXT NOT NULL,
    intent_type VARCHAR(50),
    fidelity_score FLOAT DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'pending', -- pending, executing, audited, failure
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 3. Audit & Reflection Layer
CREATE TABLE IF NOT EXISTS mission_audits (
    audit_id SERIAL PRIMARY KEY,
    mission_id UUID REFERENCES missions(mission_id) ON DELETE CASCADE,
    fidelity_score FLOAT NOT NULL,
    alignment_score FLOAT,
    grounding_score FLOAT,
    resonance_score FLOAT,
    issues JSONB,
    fix_strategy TEXT,
    hallucination_detected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Semantic Intelligence traits (Draft Storage)
CREATE TABLE IF NOT EXISTS intelligence_traits (
    trait_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(uid),
    pattern TEXT,
    context TEXT,
    significance FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Autonomous Evolution & Global Rules (v9.8.1)
CREATE TABLE IF NOT EXISTS sovereign_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_pattern TEXT UNIQUE NOT NULL,
    result_data JSONB NOT NULL,
    fidelity_score FLOAT DEFAULT 0.0,
    use_count INTEGER DEFAULT 1,
    is_promoted BOOLEAN DEFAULT FALSE,
    last_validated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Long-Horizon Goal Autonomy (v13.0.0)
CREATE TABLE IF NOT EXISTS goals (
    goal_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(uid),
    objective TEXT NOT NULL,
    success_criteria JSONB,
    priority VARCHAR(20) DEFAULT 'medium',
    state VARCHAR(20) DEFAULT 'active',
    self_correction_weight FLOAT DEFAULT 0.5,
    is_long_horizon BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. DCN Neural Synk Logs (Distributed Collective)
CREATE TABLE IF NOT EXISTS dcn_sync_logs (
    sync_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    swarm_id VARCHAR(255) NOT NULL,
    sync_type VARCHAR(50), -- IMPORT, EXPORT
    fragments_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'SUCCESS',
    protocol_version VARCHAR(20) DEFAULT 'v13.0.0',
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Performance Hardening (Composite B-Tree Indexes)
CREATE INDEX IF NOT EXISTS idx_missions_user_time ON missions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_goals_user_state ON goals (user_id, state);
CREATE INDEX IF NOT EXISTS idx_rules_pattern ON sovereign_rules (task_pattern);
CREATE INDEX IF NOT EXISTS idx_sync_swarm_time ON dcn_sync_logs (swarm_id, created_at DESC);

-- 9. Autonomous System Self-Repair (v13.0.0 Hard Hand)
CREATE TABLE IF NOT EXISTS system_patches (
    patch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(100),
    strategy TEXT,
    risk_score FLOAT,
    confidence FLOAT,
    status VARCHAR(50) DEFAULT 'pending_auditor', -- applied_autonomous, pending_auditor
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    audited_at TIMESTAMP WITH TIME ZONE
);

-- 10. Agentic Ecosystem Fabric (v13.0.0 Unity)
CREATE TABLE IF NOT EXISTS agent_insights (
    insight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    topic TEXT,
    data JSONB,
    tag VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_insights_session ON agent_insights (session_id);
