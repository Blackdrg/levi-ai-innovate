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
    TIER_MAP = {
        "L1": os.getenv("MODEL_TIER_L1", "llama3.1:8b"),
        "L2": os.getenv("MODEL_TIER_L2", "llama3.1:8b"),
        "L3": os.getenv("MODEL_TIER_L3", "llama3.1:70b"),
        "L4": os.getenv("MODEL_TIER_L4", "llama3.1:70b"),
    }

    @classmethod
    def get_model_for_tier(cls, tier: str, session_id: str = None, complexity: float = 1.0) -> str:
        """
        Sovereign v15.0: Phase 7 Infra Load Shift.
        Dynamically routes to local vs. cloud fallback based on live node pressure.
        """
        from backend.core.executor.guardrails import capture_resource_pressure
        from backend.config.system import CLOUD_FALLBACK_ENABLED
        
        # 1. Infra Load Shift (Phase 7): Check local VRAM & CPU load
        try:
            from backend.utils.hardware import gpu_monitor
            vram_usage = gpu_monitor.get_vram_usage()
            is_vram_strained = vram_usage.get("percent", 0) > 85.0
        except Exception:
            is_vram_strained = False
            
        pressure = capture_resource_pressure(is_vram_strained, 0)
        if pressure.cpu_percent > 85.0 or pressure.ram_percent > 90.0 or pressure.vram_pressure:
            if CLOUD_FALLBACK_ENABLED and tier in ["L3", "L4"]:
                logger.warning(f"⚖️ [Load Shift] High local node pressure (CPU: {pressure.cpu_percent}%, VRAM Strained: {pressure.vram_pressure}). Shifting {tier} task to cloud.")
                return "cloud-overflow-tier"
        else:
            # Force local if under threshold
            logger.debug(f"⚖️ [Load Shift] Local load nominal ({pressure.cpu_percent}% CPU). Retaining task on edge.")

        # Overriding expensive tiers for extremely low complexity (Token Cost Optimization)
        if tier in ["L3", "L4"] and complexity < 0.25:
            logger.info(f"[ModelRouter] Token Optimization: Downgrading {tier} task due to low complexity ({complexity}).")
            tier = "L1"

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

    @classmethod
    async def warm_models(cls):
        """v14.1 JIT Warming: Pre-loads essential models to reduce cold-start latency."""
        logger.info("[ModelRouter] Initiating JIT model warming pulse...")
        from backend.services.brain_service import brain_service
        
        # Warm L1/L2 models (most frequently used)
        essential_models = {cls.TIER_MAP["L1"], cls.TIER_MAP["L2"]}
        for model in essential_models:
            try:
                # We send a tiny empty prompt to trigger loading in Ollama
                await brain_service.call_local_llm(" ", model=model)
                logger.debug(f"[ModelRouter] Warmed model: {model}")
            except Exception as e:
                logger.warning(f"[ModelRouter] Failed to warm {model}: {e}")
        logger.info("[ModelRouter] JIT warming pulse complete.")
