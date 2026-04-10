"""
LEVI-AI Evolutionary Intelligence Engine (v14.1)
Hardened self-improvement engine managing fragility tracking and pattern graduation.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import select, update, insert
from backend.db.postgres import PostgresDB
from backend.db.models import GraduatedRule, FragilityIndex, Mission, TrainingPattern

logger = logging.getLogger(__name__)

class EvolutionaryIntelligenceEngine:
    """
    Sovereign Evolution Engine v14.1.
    Unifies Fragility Tracking and Deterministic Rule Graduation.
    """
    
    MIN_HITS_FOR_STABILITY = 5
    FIDELITY_GRADUATION_THRESHOLD = 0.95
    BYPASS_FIDELITY_THRESHOLD = 0.995 # Tier-1 Bypass
    
    @classmethod
    async def record_outcome(cls, user_id: str, domain: str, fidelity: float, query: str, response: str):
        """Processes mission outcome to update fragility and track patterns."""
        await cls._update_fragility(user_id, domain, fidelity)
        await cls._track_pattern(query, response, fidelity)

    @classmethod
    async def get_fragility(cls, user_id: str, domain: str) -> float:
        """Retrieves the current fragility score for a domain."""
        try:
            async with PostgresDB._session_factory() as session:
                stmt = select(FragilityIndex).where(
                    FragilityIndex.user_id == user_id,
                    FragilityIndex.domain == domain
                )
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                return record.fragility_score if record else 0.0
        except Exception as e:
            logger.error(f"[Evolution] Failed to fetch fragility: {e}")
            return 0.0

    @classmethod
    async def check_rules(cls, query: str) -> Optional[Dict[str, Any]]:
        """
        Checks for a graduated rule match and returns the result with override policy.
        LEVI Spec v14.1 Tiered Critic Logic.
        """
        try:
            task_key = query.lower().strip()
            async with PostgresDB._session_factory() as session:
                stmt = select(GraduatedRule).where(GraduatedRule.task_pattern == task_key)
                result = await session.execute(stmt)
                rule = result.scalar_one_or_none()
                
                if not rule:
                    return None

                # LEVI Spec v14.1 Logic
                policy = {
                    "tier_0_required": True,
                    "tier_1_bypass": False,
                    "tier_2_required": False
                }

                # Tier-1 Bypass Check
                if (rule.fidelity_score >= cls.BYPASS_FIDELITY_THRESHOLD and 
                    rule.is_stable and 
                    not cls._detect_system_drift()):
                    policy["tier_1_bypass"] = True
                
                # Tier-2 High-Impact Check (Example: sensitive domains or low fidelity)
                if rule.fidelity_score < 0.96:
                    policy["tier_2_required"] = True

                # Update usage stats in background
                await cls._increment_rule_usage(rule.id)
                
                return {
                    "result_data": rule.result_data,
                    "fidelity": rule.fidelity_score,
                    "policy": policy,
                    "tag": "FAST_PATH_EVOLVED"
                }

        except Exception as e:
            logger.error(f"[Evolution] Rule check failure: {e}")
            return None

    @classmethod
    async def _update_fragility(cls, user_id: str, domain: str, fidelity: float):
        """Updates the fragility index based on fidelity streaks."""
        try:
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    stmt = select(FragilityIndex).where(
                        FragilityIndex.user_id == user_id,
                        FragilityIndex.domain == domain
                    )
                    result = await session.execute(stmt)
                    record = result.scalar_one_or_none()
                    
                    if not record:
                        record = FragilityIndex(user_id=user_id, domain=domain)
                        session.add(record)
                    
                    # Calculation Logic: 
                    # Success streak reduces fragility (-20% per success > 0.9)
                    # Failures build fragility (+40% per failure < 0.7)
                    if fidelity >= 0.9:
                        record.success_streak += 1
                        record.failure_count = 0
                        record.fragility_score = max(0.0, record.fragility_score - 0.2)
                    elif fidelity < 0.7:
                        record.failure_count += 1
                        record.success_streak = 0
                        record.fragility_score = min(1.0, record.fragility_score + 0.4)
                    
                    record.weighted_fidelity = (record.weighted_fidelity * 0.7) + (fidelity * 0.3)
                    record.last_updated = datetime.now(timezone.utc)
                await session.commit()
        except Exception as e:
            logger.error(f"[Evolution] Fragility update failure: {e}")

    @classmethod
    async def _track_pattern(cls, query: str, response: str, fidelity: float):
        """Tracks repeating patterns and graduates them if they exceed thresholds."""
        if fidelity < cls.FIDELITY_GRADUATION_THRESHOLD:
            return

        try:
            task_key = query.lower().strip()
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    stmt = select(GraduatedRule).where(GraduatedRule.task_pattern == task_key)
                    result = await session.execute(stmt)
                    rule = result.scalar_one_or_none()
                    
                    if not rule:
                        rule = GraduatedRule(
                            task_pattern=task_key,
                            result_data={"solution": response},
                            fidelity_score=fidelity,
                            uses_count=1
                        )
                        session.add(rule)
                    else:
                        rule.uses_count += 1
                        rule.fidelity_score = (rule.fidelity_score * (rule.uses_count - 1) + fidelity) / rule.uses_count
                        
                        # Stability Graduation
                        if rule.uses_count >= cls.MIN_HITS_FOR_STABILITY and rule.fidelity_score >= cls.FIDELITY_GRADUATION_THRESHOLD:
                            rule.is_stable = True
                            logger.info(f"[Evolution] Rule STABILIZED: {task_key[:30]}...")
                            
                    rule.last_validated_at = datetime.now(timezone.utc)
                await session.commit()
        except Exception as e:
            logger.error(f"[Evolution] Pattern tracking failure: {e}")

    @classmethod
    async def _increment_rule_usage(cls, rule_id: int):
        """Increments rule usage count."""
        try:
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    await session.execute(
                        update(GraduatedRule).where(GraduatedRule.id == rule_id).values(uses_count=GraduatedRule.uses_count + 1)
                    )
                await session.commit()
        except Exception as e:
            logger.error(f"[Evolution] Failed to increment rule usage: {e}")

    @classmethod
    def _detect_system_drift(cls) -> bool:
        """
        Placeholder for system drift detection.
        In production, this would check if the core model version has changed
        or if global fidelity metrics have dropped significantly.
        """
        return False
