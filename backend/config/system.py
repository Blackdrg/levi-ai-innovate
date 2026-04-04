# backend/config/system.py
"""Centralized configuration for LEVI AI Tiers and Costs."""
import os

TIERS = {
    "free": {
        "daily_limit": 100, 
        "priority": 0, 
        "features": ["standard_memory"],
        "models": ["llama-3.1-8b-instant"]
    },
    "pro": {
        "daily_limit": 1000, 
        "priority": 1, 
        "features": ["ltm", "high_reasoning", "search"],
        "models": ["llama-3.1-70b-versatile", "mixtral-8x7b"]
    },
    "creator": {
        "daily_limit": 5000, 
        "priority": 2, 
        "features": ["video", "ltm", "high_reasoning", "search"],
        "models": ["llama-3.1-70b-versatile", "mixtral-8x7b", "qwen-2.5-72b"]
    }
}

COST_MATRIX = {
    "chat": 1,
    "search": 1,
    "code": 2,
    "image": 5,
    "video": 10
}

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
SECRET_KEY = os.getenv("SECRET_KEY") # No default fallback for production safety

# Production Domain: https://levi-ai.com
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://levi-ai.com").split(",")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Resilience Settings
FAILURE_THRESHOLD = 5
RETRY_DELAY = 2.0
