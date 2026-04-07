import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ModelRouter:
    """
    Sovereign Model Router v13.1.
    Maps Agent Tiers to specific LLM models based on hardware constraints and task complexity.
    """
    
    TIER_MAP = {
        "L1": os.getenv("MODEL_L1", "phi3:mini"),
        "L2": os.getenv("MODEL_L2", "llama3.1:8b"),
        "L3": os.getenv("MODEL_L3", "llama3.3:70b-instruct-q4_K_M"),
        "L4": os.getenv("MODEL_L4", "llama3.3:70b-instruct-q4_K_M")
    }

    @classmethod
    def get_model_for_tier(cls, tier: str) -> str:
        """Returns the model tag for a given tier."""
        model = cls.TIER_MAP.get(tier, cls.TIER_MAP["L2"])
        logger.debug(f"[ModelRouter] Tier {tier} mapped to {model}")
        return model

    @classmethod
    def get_all_assignments(cls) -> Dict[str, str]:
        """Returns the current model routing table."""
        return cls.TIER_MAP
