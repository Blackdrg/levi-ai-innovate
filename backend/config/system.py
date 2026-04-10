# backend/config/system.py
"""Centralized configuration for LEVI-AI Sovereign OS v14.0.0 Graduation."""
import os

SOVEREIGN_VERSION = os.getenv("SOVEREIGN_VERSION", "v14.0.0-Autonomous-SOVEREIGN")
STABILITY_BASELINE_TAG = os.getenv("STABILITY_BASELINE_TAG", "v14.0.0-STABLE-BASELINE")
ARCHITECTURE_FREEZE = {
    "agent_registry": "frozen",
    "dag_structure_format": "frozen",
    "memory_schema": "frozen",
}
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

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

SECRET_KEY = os.getenv("SECRET_KEY", "sovereign_os_genesis_key")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Disaster Recovery & Backup Settings
DR_RTO_SECONDS = 300      # Recovery Time Objective: 5 minutes
DR_RPO_SECONDS = 3600     # Recovery Point Objective: 1 hour
FAISS_SNAPSHOT_INTERVAL_MINUTES = 30
POSTGRES_WAL_BACKUP_ENABLED = True
NEO4J_BACKUP_INTERVAL_HOURS = 12
REDIS_APPENDFSYNC = "everysec"

# Resilience Settings
FAILURE_THRESHOLD = 5
RETRY_DELAY = 2.0
CLOUD_FALLBACK_ENABLED = os.getenv("CLOUD_FALLBACK_ENABLED", "false").lower() == "true"

# Cognitive Safety Gates
# Calibrated via 'calibrate_cu.py' script. 
# Re-calibrated (v14.0 Graduation): 500 CU for L3 reasoning tasks.
CU_ABORT_THRESHOLD = int(os.getenv("CU_ABORT_THRESHOLD", "500"))
CU_WARNING_PERCENT = 0.7  # Trigger warning at 70% of ceiling
HITL_STRICT_MODE = True  # Block DRAFT quality delivery
CRITIC_CALIBRATION_OFFSET = 0.0 # Weekly adjustment value
def verify_production_secrets():
    """
    Sovereign v14.1 Security Gate: Fail-Hard Production Guardrails.
    Prevents the system from booting with insecure or default secrets.
    """
    if ENVIRONMENT.lower() != "production":
        return

    # 1. Secret Key Hardening
    if len(SECRET_KEY) < 32:
        raise SystemExit("[CRITICAL] Insecure SECRET_KEY: Must be at least 32 characters in production.")
    
    if SECRET_KEY == "sovereign_os_genesis_key":
        raise SystemExit("[CRITICAL] Default SECRET_KEY detected in production!")

    # 2. JWT Configuration
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret or jwt_secret == "dev_jwt_secret_placeholder":
         raise SystemExit("[CRITICAL] Insecure or missing JWT_SECRET in production.")

    # 3. Hardware / Environment Bounds
    max_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "32768"))
    if max_tokens > 128000:
        # Prevent OOM on standard L4/A100 instances unless overridden with intent
        import warnings
        warnings.warn("Extreme MAX_CONTEXT_TOKENS detected. Verify VRAM backpressure limits.")

    print(f"[System] Production Hardening Verified: env={ENVIRONMENT}, version={SOVEREIGN_VERSION}")

# Execute Gate
verify_production_secrets()
