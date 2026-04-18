import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, update
from backend.db.postgres import PostgresDB
from backend.db.models import Mission
import asyncio

logger = logging.getLogger(__name__)

class PolicyGradientEngine:
    """
    Sovereign Policy Gradient Engine v15.0 [ACTIVE].
    Optimizes agent hyper-parameters (Temperature, Top_P, Model Choice) 
    using mission fidelity as a reward signal.
    """
    
    FIDELITY_THRESHOLD = 0.85
    
    DEFAULT_POLICY = {
        "temperature": 0.7,
        "top_p": 0.9,
        "model": "llama3.1:8b",
        "max_tokens": 1024
    }

    @classmethod
    async def get_optimal_params(cls, agent_type: str, domain: str = "default", mission_id: str = "default") -> Dict[str, Any]:
        """
        Retrieves the optimized policy for a specific agent and domain.
        v16.2: Uses PPO policy network to select actions (temperature).
        """
        try:
            from backend.core.evolution.ppo_engine import ppo_engine
            # State vector: [base_fidelity, base_latency, complexity, risk]
            state = [0.85, 0.5, 0.4, 0.2] 
            optimized_temp = ppo_engine.select_action(mission_id, state)
            
            return {
                "temperature": optimized_temp,
                "top_p": 0.9,
                "model": "llama3.1:8b",
                "max_tokens": 1024
            }
        except Exception as e:
            logger.error(f"[PolicyGradient] PPO selection failed: {e}")
            return cls.DEFAULT_POLICY

    @classmethod
    async def update_policy(cls, mission_id: str, fidelity: float):
        """
        Updates the internal policy weights based on a mission's outcome.
        v16.2: Uses PPO record_experience with critic score as reward.
        """
        logger.info(f"📊 [PolicyGradient] Recording experience for mission {mission_id} (Reward: {fidelity:.2f})")
        
        try:
            from backend.core.evolution.ppo_engine import ppo_engine
            await ppo_engine.record_experience(mission_id, reward=fidelity)
        except Exception as e:
            logger.error(f"[PolicyGradient] Policy update failed: {e}")

    @classmethod
    async def run_optimization_pass(cls):
        """
        Sovereign v16.2: Real PPO Training Pass.
        """
        logger.info("🤖 [PolicyGradient] Starting real PPO optimization pass...")
        from backend.core.evolution.ppo_engine import ppo_engine
        await ppo_engine.train_step()

policy_gradient = PolicyGradientEngine()
