# backend/config/system.py
"""Centralized configuration for LEVI-AI v1.0.0-RC1."""
import os

SOVEREIGN_VERSION = os.getenv("SOVEREIGN_VERSION", "v1.0.0-RC1")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

TIERS = {
    "guest": {
        "daily_limit": 0, 
        "priority": 0, 
        "features": ["read_only"],
        "models": []
    },
    "pro": {
        "daily_limit": 100, 
        "priority": 1, 
        "features": ["chat", "ltm", "search"],
        "models": ["llama3.1:8b", "phi3:mini"]
    },
    "creator": {
        "daily_limit": 5000, 
        "priority": 2, 
        "features": ["all_tools", "vault_access", "system_override"],
        "models": ["llama3.1:8b", "llama3.3:70b", "phi3:mini"]
    }
}

COST_MATRIX = {
    "chat": 1,
    "search": 1,
    "code": 2,
    "image": 5,
    "video": 10
}

SECRET_KEY = os.getenv("SECRET_KEY", "sovereign_monolith_genesis_key")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Resilience Settings
FAILURE_THRESHOLD = 5
RETRY_DELAY = 2.0
CLOUD_FALLBACK_ENABLED = os.getenv("CLOUD_FALLBACK_ENABLED", "false").lower() == "true"
