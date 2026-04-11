"""
LEVI-AI Evolutionary Intelligence Engine (v14.1)
Hardened self-improvement engine managing fragility tracking and pattern graduation.
"""

import logging
import json
import time
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
    DOMAIN_THRESHOLDS = {
        "code": 20,
        "security": 20,
        "finance": 20,
        "chat": 10,
        "search": 10,
        "default": 10
    }
    FIDELITY_GRADUATION_THRESHOLD = 0.95
    BYPASS_FIDELITY_THRESHOLD = 0.995 
    DIVERGENCE_QUARANTINE_THRESHOLD = 3 
    
    @classmethod
    async def record_outcome(cls, user_id: str, domain: str, fidelity: float, query: str, response: str):
        """Processes mission outcome to update fragility and track patterns."""
        await cls._update_fragility(user_id, domain, fidelity)
        await cls._track_pattern(query, response, fidelity, domain=domain)

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
                    not rule.is_quarantined and
                    not cls._detect_system_drift()):
                    policy["tier_1_bypass"] = True
                
                # Tier-2 High-Impact Check (Example: sensitive domains or low fidelity)
                if rule.fidelity_score < 0.96 or rule.is_quarantined:
                    policy["tier_2_required"] = True

                if rule.is_quarantined:
                    logger.debug(f"[Evolution] Rule {rule.id} matches but is QUARANTINED. Requiring shadow verification.")
                    return None

                # Update usage stats in background
                await cls._increment_rule_usage(rule.id)
                
                return {
                    "rule_id": rule.id,
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
    async def record_shadow_outcome(cls, rule_id: int, matches_llm: bool):
        """
        Sovereign v15.0: Shadow Outcome Processor.
        Updates drift metrics and quarantines rules if they diverge consistently.
        """
        try:
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    rule = await session.get(GraduatedRule, rule_id)
                    if not rule: return

                    rule.shadow_audit_count += 1
                    if not matches_llm:
                        rule.divergence_count += 1
                        # Drift score is a simple ratio of failures to audits for this rule
                        rule.drift_score = rule.divergence_count / rule.shadow_audit_count
                        
                        logger.warning(f"⚠️ [Evolution] Shadow Divergence for Rule {rule_id} ({rule.divergence_count}/{cls.DIVERGENCE_QUARANTINE_THRESHOLD})")
                        
                        if rule.divergence_count >= cls.DIVERGENCE_QUARANTINE_THRESHOLD:
                            rule.is_quarantined = True
                            rule.is_stable = False
                            logger.critical(f"🚨 [Evolution] Rule {rule_id} QUARANTINED due to sustained accuracy drift.")
                    else:
                        rule.divergence_count = 0 # Reset on success (Phase 3 Margin)
                        rule.drift_score = rule.divergence_count / rule.shadow_audit_count

                await session.commit()
        except Exception as e:
            logger.error(f"[Evolution] Shadow record failure: {e}")

    @classmethod
    async def on_rule_graduated(cls, rule_id: int):
        """
        Callback triggered when a rule graduates to 'STABLE'.
        Performs Redis sync and broadcasts a telemetry pulse.
        """
        try:
            from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC
            if not HAS_REDIS_ASYNC or not redis_client:
                return

            async with PostgresDB._session_factory() as session:
                rule = await session.get(GraduatedRule, rule_id)
                if not rule or not rule.is_stable:
                    return

                # Write to Fast-Path Routing Table
                await redis_client.hset(
                    "sovereign:fast_path:rules",
                    rule.task_pattern,
                    json.dumps(rule.result_data)
                )
                
                # Notification Pulse (v15.0 Transparency)
                from backend.broadcast_utils import SovereignBroadcaster
                SovereignBroadcaster.publish("RULE_GRADUATED", {
                    "rule_id": rule.id,
                    "pattern": rule.task_pattern[:50],
                    "fidelity": rule.fidelity_score,
                    "msg": "Intelligence Crystallized: New Fast-Path active."
                }, user_id="global")
                
                logger.info(f"🎓 [Evolution] Rule {rule_id} Graduated to Fast-Path.")

                # DCN Swarm Pulse
                try:
                    from backend.core.dcn_protocol import DCNProtocol
                    dcn = DCNProtocol()
                    await dcn.broadcast_gossip(
                        mission_id="swarm_evolution",
                        payload={"rule_id": rule_id, "pattern": rule.task_pattern, "fidelity": rule.fidelity_score},
                        pulse_type="rule_graduated"
                    )
                except Exception: pass
                
        except Exception as e:
            logger.error(f"[Evolution] Graduation callback failure: {e}")

    @classmethod
    async def _perform_drift_check(cls, rule_id: int):
        """
        Sovereign v14.2: Rule Accuracy Drift Detection.
        Re-validates a graduated rule against a fresh Model synthesis.
        """
        try:
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    rule = await session.get(GraduatedRule, rule_id)
                    if not rule: return

                    logger.info(f"[Evolution] Performing shadow-drift check for Rule {rule_id}...")
                    
                    # 1. Simulate fresh synthesis (In prod: call ToolRegistry or dedicated Evaluator)
                    # For RC1: We check if the pattern still yields high fidelity.
                    # If quarantine period (24h) is over and fidelity is stable, lift quarantine.
                    if rule.created_at:
                        age_hours = (datetime.now(timezone.utc) - rule.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                        if age_hours >= 24 and rule.fidelity_score >= cls.FIDELITY_GRADUATION_THRESHOLD:
                            rule.is_quarantined = False
                            rule.last_drift_check = datetime.now(timezone.utc)
                            logger.info(f"[Evolution] 🛡️ QUARANTINE LIFTED for Rule {rule_id} after {age_hours:.1f}h stability.")
        except Exception as e:
            logger.error(f"[Evolution] Drift check failure for {rule_id}: {e}")

    @classmethod
    async def _track_pattern(cls, query: str, response: str, fidelity: float, domain: str = "default"):
        """Tracks repeating patterns and graduates them if they exceed thresholds."""
        if fidelity < cls.FIDELITY_GRADUATION_THRESHOLD:
            return

        try:
            task_key = query.lower().strip()
            threshold = cls.DOMAIN_THRESHOLDS.get(domain, cls.DOMAIN_THRESHOLDS["default"])
            
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
                        
                        # Stability Graduation (Domain Specific)
                        if rule.uses_count >= threshold and rule.fidelity_score >= cls.FIDELITY_GRADUATION_THRESHOLD:
                            if not rule.is_stable:
                                rule.is_stable = True
                                logger.info(f"[Evolution] Rule STABILIZED for domain '{domain}': {task_key[:30]}...")
                                from backend.utils.runtime_tasks import create_tracked_task
                                create_tracked_task(cls.on_rule_graduated(rule.id), name=f"graduation-{rule.id}")
                            
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
