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
