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
    async def get_optimal_params(cls, agent_type: str, domain: str = "default") -> Dict[str, Any]:
        """
        Retrieves the optimized policy for a specific agent and domain.
        Uses historical fidelity scores to weight better parameters.
        """
        try:
            async with PostgresDB._session_factory() as session:
                from backend.db.models import AgentPolicy
                stmt = select(AgentPolicy).where(AgentPolicy.agent_type == agent_type, AgentPolicy.domain == domain)
                result = await session.execute(stmt)
                policy = result.scalar_one_or_none()
                
                if policy:
                    return {
                        "temperature": policy.temperature,
                        "top_p": policy.top_p,
                        "model": policy.model,
                        "max_tokens": policy.max_tokens
                    }
                return cls.DEFAULT_POLICY
                
        except Exception as e:
            logger.error(f"[PolicyGradient] Parameter estimation failed: {e}")
            return cls.DEFAULT_POLICY

    @classmethod
    async def update_policy(cls, mission_id: str, fidelity: float):
        """
        Updates the internal policy weights based on a mission's outcome.
        Reward = Fidelity - Baseline.
        """
        if fidelity < cls.FIDELITY_THRESHOLD: return
        
        logger.info(f"📊 [PolicyGradient] Reinforcing policy for mission {mission_id} (Fidelity: {fidelity:.2f})")
        
        try:
            async with PostgresDB._session_factory() as session:
                from backend.db.models import Mission, AgentPolicy
                # Get mission to identify domain and agent params used
                stmt = select(Mission).where(Mission.mission_id == mission_id)
                res = await session.execute(stmt)
                mission = res.scalar_one_or_none()
                
                if not mission: return
                
                domain = mission.intent_type or "default"
                # For GA, we specifically optimize the 'planner' agent for now
                agent_type = "planner" 
                
                # Upsert policy logic
                from sqlalchemy.dialects.postgresql import insert
                stmt = insert(AgentPolicy).values(
                    agent_type=agent_type,
                    domain=domain,
                    fidelity_avg=fidelity,
                    samples=1
                ).on_conflict_do_update(
                    index_elements=['agent_type', 'domain'],
                    set_={
                        "fidelity_avg": (AgentPolicy.fidelity_avg * AgentPolicy.samples + fidelity) / (AgentPolicy.samples + 1),
                        "samples": AgentPolicy.samples + 1,
                        "last_updated": func.now()
                    }
                )
                await session.execute(stmt)
                await session.commit()
                
        except Exception as e:
            logger.error(f"[PolicyGradient] Policy update failed: {e}")

    @classmethod
    async def run_optimization_pass(cls):
        """
        Sovereign v16.0: SPPO (Simple Policy Proximal Optimization) Bridge.
        Fine-tunes agent parameters via Reinforcement Learning using mission fidelity as Reward.
        """
        logger.info("🤖 [PolicyGradient] Starting SPPO optimization pass...")
        
        async with PostgresDB._session_factory() as session:
            from backend.db.models import AgentPolicy
            # 1. Fetch policies that have enough samples for a gradient estimate
            stmt = select(AgentPolicy).where(AgentPolicy.samples >= 5)
            res = await session.execute(stmt)
            policies = res.scalars().all()
            
            for policy in policies:
                # 2. Advantage Calculation (Fidelity - Baseline 0.8)
                # Policy gradient logic: theta = theta + alpha * Advantage * gradient(log(pi))
                advantage = policy.fidelity_avg - 0.8
                lr = 0.05 # Learning Rate
                
                if advantage > 0:
                    # Positive Reinforcement: Nudge towards more deterministic/precise behavior
                    # (Decrease temperature, increase top_p)
                    nudge = lr * advantage
                    policy.temperature = max(0.1, min(1.0, policy.temperature - nudge))
                    policy.top_p = min(1.0, policy.top_p + (nudge * 0.5))
                    logger.info(f"📈 [SPPO] REINFORCE {policy.agent_type}: Temp -> {policy.temperature:.3f} (Advantage: {advantage:.2f})")
                else:
                    # Negative Reinforcement: Increase exploratory entropy
                    # (Increase temperature slightly to find better paths)
                    exploration_nudge = lr * abs(advantage)
                    policy.temperature = min(0.9, policy.temperature + exploration_nudge)
                    logger.info(f"📉 [SPPO] EXPLORE {policy.agent_type}: Temp -> {policy.temperature:.3f} (Penalty: {advantage:.2f})")
                
                policy.last_updated = func.now()
            
            await session.commit()



policy_gradient = PolicyGradientEngine()
