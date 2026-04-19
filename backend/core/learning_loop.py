import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional, List
from sqlalchemy import select, desc, func, update
from sqlalchemy.dialects.postgresql import insert
from backend.db.postgres import PostgresDB
from backend.db.models import (
    TrainingPattern, 
    EvolutionMetric, 
    SuccessPattern, 
    FailurePattern, 
    GraduatedRule
)

logger = logging.getLogger(__name__)

class LearningLoop:
    """
    Sovereign v15.0: CLOSED LEARNING LOOP.
    System learns from every execution by capturing traces, 
    analyzing patterns, and graduating high-fidelity deterministic rules.
    """
    
    FIDELITY_THRESHOLD = 0.85
    EVOLUTION_TRIGGER_COUNT = 50 # Run analysis every 50 missions
    ENABLED = True

    @classmethod
    async def crystallize_pattern(
        cls,
        mission_id: str,
        query: str,
        result: str,
        fidelity: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Step 2.1: Crystallize Execution Traces for Evolution."""
        if not cls.ENABLED: return
        
        metadata = metadata or {}
        user_id = metadata.get("user_id", "default")
        intent_type = metadata.get("intent_type", "chat")
        
        logger.info(f"[LearningLoop] Capturing outcome for mission {mission_id} (Fidelity: {fidelity:.2f})")

        try:
            async with await PostgresDB.get_session() as session:
                async with session.begin():
                    # 1. Store Detailed Evolution Metric (Trace)
                    metric = EvolutionMetric(
                        mission_id=mission_id,
                        accuracy_score=fidelity,
                        latency_ms=metadata.get("latency_ms", 0),
                        status="success" if fidelity >= cls.FIDELITY_THRESHOLD else "failure",
                        metadata_json={
                            "query": query,
                            "plan": metadata.get("graph_template", []),
                            "agents_used": metadata.get("agent_sequence", []),
                            "reasoning_strategy": metadata.get("reasoning_strategy", {}),
                            "intent_type": intent_type,
                            "user_id": user_id
                        }
                    )
                    session.add(metric)
                    
                    # 2. Legacy Training Pattern (Optional LoRA)
                    if fidelity >= cls.FIDELITY_THRESHOLD:
                        stmt = insert(TrainingPattern).values(
                            mission_id=mission_id,
                            query=query,
                            result=result,
                            fidelity_score=fidelity
                        ).on_conflict_do_nothing(index_elements=['mission_id'])
                        await session.execute(stmt)

                await session.commit()
            
            # --- [Phase 16.2] Real PPO Loop: Optimize Hyper-parameters ---
            from backend.core.evolution.ppo_engine import ppo_engine
            # Reward = fidelity normalized to [-1, 1]
            reward = (fidelity - 0.5) * 2
            await ppo_engine.record_experience(mission_id, reward)
            
            # 3. Check for Evolution Trigger
            await cls._check_evolution_trigger()

        except Exception as e:
            logger.error(f"[LearningLoop] Failed to capture outcome: {e}")

    @classmethod
    async def _check_evolution_trigger(cls):
        """Triggers the feedback engine after a certain number of missions."""
        try:
            async with await PostgresDB.get_session() as session:
                stmt = select(func.count()).select_from(EvolutionMetric).where(EvolutionMetric.status == "success")
                res = await session.execute(stmt)
                count = res.scalar() or 0
                
                if count % cls.EVOLUTION_TRIGGER_COUNT == 0 and count > 0:
                    logger.info(f"[LearningLoop] Evolution Trigger: Analyzing {count} traces...")
                    asyncio.create_task(cls.analyze_traces())
        except Exception as e:
            logger.error(f"[LearningLoop] Evolution trigger check failed: {e}")

    @classmethod
    async def analyze_traces(cls):
        """Step 2.2: Build Feedback Engine - Identify successful patterns and repeated failures."""
        logger.info("[LearningLoop] Feedback Engine: Analyzing recent mission traces...")
        try:
            async with await PostgresDB.get_session() as session:
                # 1. Distill SUCCESSFUL Patterns
                stmt = select(EvolutionMetric).where(
                    EvolutionMetric.accuracy_score >= 0.95,
                    EvolutionMetric.status == "success"
                ).order_by(EvolutionMetric.timestamp.desc()).limit(100)
                
                results = await session.execute(stmt)
                metrics = results.scalars().all()
                
                for m in metrics:
                    meta = m.metadata_json
                    query = meta.get("query", "")
                    agents = meta.get("agents_used", [])
                    
                    if not query or not agents: continue
                    
                    # Normalize query slightly for pattern matching
                    pattern_key = query.lower().strip()[:200]
                    
                    # Upsert into SuccessPattern
                    stmt = insert(SuccessPattern).values(
                        objective_pattern=pattern_key,
                        agent_sequence=agents,
                        fidelity_avg=m.accuracy_score,
                        win_count=1
                    ).on_conflict_do_update(
                        index_elements=['objective_pattern'],
                        set_={
                            "fidelity_avg": (SuccessPattern.fidelity_avg + m.accuracy_score) / 2,
                            "win_count": SuccessPattern.win_count + 1,
                            "last_used_at": func.now()
                        }
                    )
                    await session.execute(stmt)

                # 2. Distill RECURRING FAILURES
                stmt = select(EvolutionMetric).where(
                    EvolutionMetric.accuracy_score < 0.6,
                    EvolutionMetric.status == "failure"
                ).limit(50)
                
                failures = await session.execute(stmt)
                for f in failures.scalars().all():
                     # Implement Failure Tracking logic
                     pass

                # 🚀 Step 2.4: Sovereign Emergence (Discovery)
                from backend.evolution.discovery import discovery_engine
                interactions = [{"query": m.metadata_json.get("query"), "agents": m.metadata_json.get("agents_used")} for m in metrics]
                await discovery_engine.identify_emergence(interactions)

                await session.commit()
                
            # 3. Step 2.3: Rule Engine Graduation
            await cls.distill_graduated_rules()

        except Exception as e:
            logger.error(f"[LearningLoop] Trace analysis failed: {e}")

    @classmethod
    async def distill_graduated_rules(cls):
        """Step 2.3: Rule Engine (REAL EVOLUTION) - Promote high-fidelity patterns to hard-coded overrides."""
        logger.info("[LearningLoop] Rule Engine: Distilling Graduated Rules...")
        try:
            async with await PostgresDB.get_session() as session:
                # Select success patterns with high win_count and high fidelity
                stmt = select(SuccessPattern).where(
                    SuccessPattern.win_count >= 5,
                    SuccessPattern.fidelity_avg >= 0.98
                )
                
                patterns_raw = await session.execute(stmt)
                patterns_list = patterns_raw.scalars().all()
                
                for p in patterns_list:
                    logger.info(f"[LearningLoop] Promoting pattern to GRADUATED RULE: {p.objective_pattern[:50]}...")
                    
                    grad_rule = insert(GraduatedRule).values(
                        task_pattern=p.objective_pattern,
                        result_data={
                            "agent_sequence": p.agent_sequence,
                            "fidelity": p.fidelity_avg,
                            "reason": "high_fidelity_reoccurrence"
                        },
                        fidelity_score=p.fidelity_avg,
                        is_stable=True
                    ).on_conflict_do_update(
                        index_elements=['task_pattern'],
                        set_={
                            "fidelity_score": p.fidelity_avg,
                            "last_validated_at": func.now()
                        }
                    )
                    await session.execute(grad_rule)

                await session.commit()
                
                # --- [Engine 13] Distributed Learning: Cross-Region Weight Sync ---
                try:
                    from backend.main import dcn_protocol
                    if dcn_protocol and dcn_protocol.is_active:
                         for p in patterns_list:
                              await dcn_protocol.sync_evolution_weights(p.objective_pattern, {
                                  "agent_sequence": p.agent_sequence,
                                  "fidelity": p.fidelity_avg
                              })
                except Exception as sync_err:
                     logger.error(f"[LearningLoop] Distributed Learning Sync Failure: {sync_err}")

        except Exception as e:
            logger.error(f"[LearningLoop] Rule distillation failure: {e}")

    @classmethod
    async def check_rules(cls, query: str) -> Optional[Dict[str, Any]]:
        """Used by the Planner to check for deterministic rule overrides."""
        try:
            pattern_key = query.lower().strip()[:200]
            async with await PostgresDB.get_session() as session:
                stmt = select(GraduatedRule).where(
                    GraduatedRule.task_pattern == pattern_key,
                    GraduatedRule.is_stable == True,
                    GraduatedRule.is_quarantined == False
                )
                result = await session.execute(stmt)
                rule = result.scalar_one_or_none()
                
                if rule:
                    logger.info(f"🎯 [RuleEngine] Match found for: '{pattern_key[:30]}...' (F={rule.fidelity_score:.2f})")
                    # Increment use count in background
                    asyncio.create_task(cls._increment_rule_usage(rule.id))
                    return rule.result_data
        except Exception as e:
             logger.error(f"[LearningLoop] Rule check failure: {e}")
        return None

    @classmethod
    async def _increment_rule_usage(cls, rule_id: int):
        try:
            async with await PostgresDB.get_session() as session:
                await session.execute(update(GraduatedRule).where(GraduatedRule.id == rule_id).values(uses_count=GraduatedRule.uses_count + 1))
                await session.commit()
        except Exception: pass
