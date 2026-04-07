import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ModelRouter:
    """
    Sovereign Model Router v13.1.
    Maps Agent Tiers to specific LLM models based on hardware constraints and task complexity.
    """
    
    SHADOW_MODE = os.getenv("SHADOW_DEPLOYMENT_ACTIVE", "false").lower() == "true"
    CANDIDATE_MODEL = os.getenv("MODEL_CANDIDATE", "llama3-fine-tuned:latest")
    SHADOW_TRAFFIC_PCT = float(os.getenv("SHADOW_TRAFFIC_PERCENT", "10.0"))

    @classmethod
    def get_model_for_tier(cls, tier: str, session_id: str = None) -> str:
        """
        Sovereign v14.0: Shadow-Aware Routing.
        Maps Agent Tiers to models, with optional A/B testing for fine-tuned candidates.
        """
        base_model = cls.TIER_MAP.get(tier, cls.TIER_MAP["L2"])
        
        # 1. Shadow Deployment Logic (A/B Testing)
        if cls.SHADOW_MODE and tier in ["L3", "L4"] and session_id:
            # Deterministic hash of session_id to ensure sticky routing
            import hashlib
            m = hashlib.md5(session_id.encode())
            bucket = int(m.hexdigest(), 16) % 100
            
            if bucket < cls.SHADOW_TRAFFIC_PCT:
                logger.info(f"[ModelRouter] 🎭 Shadow Routing active for {session_id}. Using candidate: {cls.CANDIDATE_MODEL}")
                return cls.CANDIDATE_MODEL
                
        logger.debug(f"[ModelRouter] Tier {tier} mapped to {base_model}")
        return base_model

    @classmethod
    def get_all_assignments(cls) -> Dict[str, str]:
        """Returns the current model routing table."""
        config = cls.TIER_MAP.copy()
        if cls.SHADOW_MODE:
            config["SHADOW_CANDIDATE"] = cls.CANDIDATE_MODEL
            config["SHADOW_PCT"] = f"{cls.SHADOW_TRAFFIC_PCT}%"
        return config
