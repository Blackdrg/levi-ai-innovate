-- Run this to complete the v13 migration
-- v13_migration.sql

-- Update existing intelligence_traits table
ALTER TABLE intelligence_traits 
    ADD COLUMN IF NOT EXISTS usage_count INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_used TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS promoted BOOLEAN DEFAULT FALSE;

-- Update existing missions table
ALTER TABLE missions
    ADD COLUMN IF NOT EXISTS fidelity_score FLOAT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;

-- The missing quarantine table from section 13.6
CREATE TABLE IF NOT EXISTS mission_quarantine (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES missions(mission_id),
    failure_reason TEXT,
    retry_count INT DEFAULT 0,
    staged_at TIMESTAMP DEFAULT NOW()
);

-- System audit log from section 13.9
CREATE TABLE IF NOT EXISTS system_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID,
    transition_from VARCHAR(50),
    transition_to VARCHAR(50),
    agent VARCHAR(100),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Episodic Memory from section 13.12
CREATE TABLE IF NOT EXISTS user_facts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    fact TEXT NOT NULL,
    importance FLOAT DEFAULT 0.5,
    mission_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Learning Loop: Training Corpus for v2.0 fine-tuning
CREATE TABLE IF NOT EXISTS training_corpus (
    id SERIAL PRIMARY KEY,
    mission_id VARCHAR(255) UNIQUE,
    query TEXT NOT NULL,
    result TEXT NOT NULL,
    fidelity_score FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
