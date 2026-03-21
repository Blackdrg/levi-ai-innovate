-- Enable the pgvector extension to work with embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    password_hash VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tier VARCHAR DEFAULT 'free',
    credits INTEGER DEFAULT 10,
    stripe_customer_id VARCHAR,
    liked_topics JSONB DEFAULT '[]',
    mood_history JSONB DEFAULT '[]',
    share_count INTEGER DEFAULT 0,
    bonus_credits INTEGER DEFAULT 0
);

-- Create quotes table
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    author VARCHAR,
    topic VARCHAR,
    mood VARCHAR,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    embedding vector(384)
);

-- Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user_memory table
CREATE TABLE IF NOT EXISTS user_memory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE,
    mood_history JSONB DEFAULT '[]',
    liked_topics JSONB DEFAULT '[]',
    interaction_count INTEGER DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create feed_items table
CREATE TABLE IF NOT EXISTS feed_items (
    id SERIAL PRIMARY KEY,
    text TEXT,
    author VARCHAR,
    mood VARCHAR,
    image_b64 TEXT,
    image_url TEXT,
    video_url TEXT,
    likes INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Create analytics table
CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE,
    chats_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    daily_users INTEGER DEFAULT 0
);
