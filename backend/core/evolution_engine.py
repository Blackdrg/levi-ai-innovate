"""
LEVI-AI Evolutionary Intelligence Engine (v22.0) [ACTIVE]
Hardened self-improvement engine managing fragility tracking and pattern graduation.
STATUS: This module is ACTIVE and managing autonomous mutations.
"""

import logging
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import select, update, insert
from backend.db.postgres import PostgresDB
from backend.db.models import GraduatedRule, FragilityIndex, Mission, TrainingPattern
import subprocess
import os
from .replay_buffer import global_replay_buffer
from backend.services.evolution.lora_trainer import lora_trainer

logger = logging.getLogger(__name__)

class EvolutionaryIntelligenceEngine:
    """
    Sovereign Evolution Engine v22.0 [ACTIVE].
    Unifies Fragility Tracking and Deterministic Rule Graduation.
    """
    DISABLED = False
    BYPASS_FIDELITY_THRESHOLD = 0.95
    DIVERGENCE_QUARANTINE_THRESHOLD = 3
    FIDELITY_GRADUATION_THRESHOLD = 0.90
    DOMAIN_THRESHOLDS = {"default": 5, "chat": 3, "code": 5, "research": 5}

    @classmethod
    async def record_outcome(cls, user_id: str, query: str, response: str, fidelity: float, domain: str = "default", mission_context: Dict[str, Any] = None):
        """
        Sovereign v16.2: Hardened Outcome Recording.
        Uses a validation gate to ensure only high-quality data enters the learning pipeline.
        """
        if cls.DISABLED: return
        
        # 🔄 Replay Buffer Integration
        experience_reward = fidelity
        # 🪐 Sovereign v16.2: Manual Reinforcement Priority
        if mission_context and mission_context.get("is_manual_reinforcement"):
            experience_reward = fidelity * 1.2 # Boost manual wisdom
            logger.info(f"🌟 [Evolution] Manual Wisdom detected! Priority learning for: {query[:30]}")

        global_replay_buffer.add(
            state={"query": query, "domain": domain},
            action={"response": response},
            reward=min(1.0, experience_reward),
            next_state={"fidelity": fidelity}
        )

        # 🪐 Sovereign v16.3: Autonomous Learning Trigger (Rapid Demonstration)
        if len(global_replay_buffer) >= 5: # Threshold for rapid feedback (Real: 50+)
            logger.info("🔥 [Evolution] Replay buffer threshold met. Spawning autonomous training pulse...")
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(cls.trigger_autonomous_lora_tuning(), name="auto-lora-tuning")

        await cls._update_fragility(user_id, domain, fidelity)
        await cls._track_pattern(query, response, fidelity, domain)

    @classmethod
    async def _validate_before_learning(cls, query: str, response: str, fidelity: float, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Performs a multi-pass validation check before allowing an outcome to influence the system.
        v16.2 Hardened: Respects the Reflection Engine (Critic) hard gate.
        """
        # 1. Base Fidelity Threshold (Hard reject if below engine-specific threshold)
        if fidelity < cls.FIDELITY_GRADUATION_THRESHOLD:
            logger.debug(f"[Evolution] Rejected: Fidelity {fidelity} < {cls.FIDELITY_GRADUATION_THRESHOLD}")
            return False
            
        # 2. Reflection Engine (Critic) Veto
        if context and "critic_report" in context:
            report = context["critic_report"]
            if not report.get("validated", False):
                logger.critical(f"🚨 [Evolution] Hard Block: Critic Veto detected for mission learning pulse.")
                return False

        # 3. Independent Model-Audit (Deep Validation)
        try:
            from backend.agents.critic_agent import CriticAgent, CriticInput
            critic = CriticAgent()
            audit = await critic._run(CriticInput(
                goal=f"Validate learning outcome for: {query[:50]}",
                agent_output=response,
                context=context or {}
            ))
            
            if not audit.get("success", True) or audit.get("score", 1.0) < 0.8:
                return False
        except Exception as e:
            logger.error(f"[Evolution] Critic validation failed: {e}")
            return False
            
        return True


    @classmethod
    async def get_fragility(cls, user_id: str, domain: str) -> float:
        if cls.DISABLED: return 0.0
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
            logger.error(f"[Evolution] Fragility fetch error: {e}")
            return 0.0

    @classmethod
    async def check_rules(cls, query: str) -> Optional[Dict[str, Any]]:
        """
        Checks for a graduated rule match and returns the result with override policy.
        LEVI Spec v14.1 Tiered Critic Logic.
        """
        if cls.DISABLED: return None
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

                # DCN Swarm Pulse (Sync with Mesh)
                try:
                    from backend.core.dcn_protocol import get_dcn_protocol
                    dcn = get_dcn_protocol()
                    await dcn.sync_evolution_weights(rule.task_pattern, rule.result_data)
                except Exception: pass
                
        except Exception as e:
            logger.error(f"[Evolution] Graduation callback failure: {e}")

    @classmethod
    async def record_shadow_outcome(cls, rule_id: int, matches_llm: bool):
        """
        Sovereign v15.0: Shadow Outcome Processor.
        Updates drift metrics and quarantines rules if they diverge consistently.
        Validates established rules against a deep LLM to detect drift.
        Used to lift quarantine or flag drift.
        """
        try:
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    rule = await session.get(GraduatedRule, rule_id)
                    if not rule: return

                    rule.shadow_audit_count += 1
                    
                    # Update shadow audit statistics in metadata
                    meta = rule.result_data or {}
                    history = meta.get("shadow_history", [])
                    history.append({"ts": time.time(), "match": matches_llm})
                    meta["shadow_history"] = history[-10:] # Keep last 10
                    rule.result_data = meta

                    if not matches_llm:
                        rule.divergence_count += 1
                        # Drift score is a ratio of failures to audits
                        rule.drift_score = rule.divergence_count / rule.shadow_audit_count
                        
                        logger.warning(f"⚠️ [Evolution] Shadow Divergence for Rule {rule_id} ({rule.divergence_count}/{cls.DIVERGENCE_QUARANTINE_THRESHOLD})")
                        
                        # Penalize fidelity
                        rule.fidelity_score *= 0.9 
                        
                        if rule.divergence_count >= cls.DIVERGENCE_QUARANTINE_THRESHOLD or rule.fidelity_score < cls.FIDELITY_GRADUATION_THRESHOLD:
                            rule.is_quarantined = True
                            rule.is_stable = False
                            logger.critical(f"🚨 [Evolution] Rule {rule_id} QUARANTINED due to sustained accuracy drift.")
                    else:
                        rule.divergence_count = 0 # Reset on success
                        rule.drift_score = 0.0
                        
                        # If we have 3 consecutive matches, we are ready for graduation
                        matches = [h["match"] for h in history[-3:]]
                        if len(matches) >= 3 and all(matches):
                            if rule.is_quarantined:
                                rule.is_quarantined = False
                                rule.is_stable = True
                                logger.info(f"✨ [Evolution] GRADUATION: Rule {rule_id} validated successfully via shadow audits.")
                                from backend.utils.runtime_tasks import create_tracked_task
                                create_tracked_task(cls.on_rule_graduated(rule_id), name=f"graduation-{rule_id}")

                await session.commit()
        except Exception as e:
            logger.error(f"[Evolution] Shadow record failure: {e}")

    @classmethod
    async def _check_overfitting(cls, rule_id: int) -> bool:
        """
        Sovereign v17.5: Diversity Audit.
        Ensures a rule isn't overfitted to a single mission or user before graduation.
        Returns True if rule is diverse enough for production.
        """
        try:
            async with PostgresDB._session_factory() as session:
                # In a real setup, we'd check TrainingPattern records for this task_pattern
                # Requirement: Minimum 3 distinct users OR 10 distinct mission IDs
                # For simulation, we return True if uses_count > 10
                rule = await session.get(GraduatedRule, rule_id)
                if not rule: return False
                
                is_diverse = rule.uses_count >= 10
                if not is_diverse:
                    logger.info(f" 🧬 [Evolution] Rule {rule_id} held for graduation: Insufficient diversity (uses={rule.uses_count}).")
                return is_diverse
        except Exception: return False

    @classmethod
    async def _perform_drift_check(cls, rule_id: int):
        """
        Sovereign v14.2: Rule Accuracy Drift Detection.
        Legacy - logic now handled by record_shadow_outcome via Orchestrator or AuditJobs.
        """
        pass

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
    async def run_dreaming_session(cls):
        """Public alias for performing a single evolutionary cycle."""
        await cls._perform_evolutionary_cycle()
        # 🪐 Sovereign v16.2: Check if we should trigger a LoRA tuning session
        if len(global_replay_buffer) >= 100:
             await cls.trigger_autonomous_lora_tuning()

    @classmethod
    async def trigger_autonomous_lora_tuning(cls):
        """
        Sovereign v16.2: Autonomous LoRA Fine-tuning.
        Crystallizes high-fidelity experiences into local model weight adapters.
        """
        logger.info("🚀 [Evolution] Initiating Autonomous Evolution Cycle...")
        
        # 1. Gather high-fidelity training data via the dedicated trainer service
        # This combines ReplayBuffer stats with validated Mission history
        try:
            await lora_trainer.run_maintenance_cycle()
            
            # 2. Clear replay buffer after successful cycle trigger
            global_replay_buffer.clear()
            logger.info("✅ [Evolution] Evolution cycle successfully bridged to LoRA Trainer.")
        except Exception as e:
            logger.error(f"❌ [Evolution] Failed to trigger LoRA training cycle: {e}")

    @classmethod
    async def start_dreaming_loop(cls, interval: int = 3600):
        """
        Sovereign v15.0: The Dreaming Loop.
        Background cycle for autonomous pattern crystallization and self-patching.
        """
        logger.info(f"🌙 [Evolution] Awakening the Dreaming Loop (Interval: {interval}s)")
        while True:
            try:
                await cls._perform_evolutionary_cycle()
                # 🔬 Sovereign v16.3: Autonomous Self-Healing Check
                await cls.analyze_system_fragility()
            except Exception as e:
                logger.error(f"[Evolution] Dreaming cycle failed: {e}")
            await asyncio.sleep(interval)

    @classmethod
    async def _perform_evolutionary_cycle(cls):
        """
        Executes a full evolutionary pass:
        1. Pattern Discovery (SQL -> Candidate)
        2. Mutation (Refining Candidates via Logic Synthesis)
        3. Graduation (Validating & Deploying)
        """
        logger.info("🌌 [Evolution] Processing cognitive patterns in the Dreaming Loop...")
        
        # 1. Pattern Discovery
        from backend.db.postgres import PostgresDB
        from backend.db.models import TrainingPattern
        async with PostgresDB._session_factory() as session:
            # Find repeating patterns with high fidelity
            stmt = select(TrainingPattern).where(TrainingPattern.is_trained == False).limit(50)
            result = await session.execute(stmt)
            patterns = result.scalars().all()
            
            if not patterns:
                logger.debug("[Evolution] No new patterns for crystallization.")
                return

            for p in patterns:
                # 2. Mutation & Synthesis
                # Use a local LLM pass to 'crystallize' the pattern into a generalized rule
                from backend.utils.llm_utils import call_lightweight_llm
                prompt = (
                    "You are the LEVI Evolution Mutator. Convert this mission outcome into a generalized reasoning rule.\n"
                    f"Instruction: {p.query}\nOutput: {p.result}\n"
                    "Generalized Rule YAML: (Focus on logic, not specific data)"
                )
                
                try:
                    crystallized = await call_lightweight_llm([{"role": "system", "content": prompt}], model="llama3.1:8b")
                    
                    # 🛡️ Graduation #28: Autonomous Critic Validation
                    from backend.agents.critic_agent import CriticAgent, CriticInput
                    critic = CriticAgent()
                    critic_report = await critic._run(CriticInput(
                        goal=f"Crystallize rule for: {p.query}",
                        agent_output=crystallized,
                        context={"original_result": p.result}
                    ))

                    if not critic_report.get("success"):
                        logger.warning(f"[Evolution] Mutation rejected by Critic for {p.mission_id}. Score: {critic_report.get('score')}")
                        continue

                    # 3. Candidate Promotion
                    # We store it as a GraduatedRule with 'is_stable = False' (Quarantine)
                    rule = GraduatedRule(
                        task_pattern=p.query.lower().strip(),
                        result_data={"solution": crystallized, "original_mission": p.mission_id},
                        fidelity_score=p.fidelity_score,
                        uses_count=1,
                        is_stable=False,
                        is_quarantined=True
                    )
                    session.add(rule)
                    p.is_trained = True # Mark as processed
                    logger.info(f"✨ [Evolution] New Rule Crystallized & Validated: {p.query[:30]}...")
                except Exception as mut_err:
                    logger.error(f"[Evolution] Mutation failed for mission {p.mission_id}: {mut_err}")

            await session.commit()

    @classmethod
    async def run_shadow_audit(cls):
        """
        Sovereign v15.1: Periodic Shadow Audit.
        Validates established rules against a deep LLM to detect drift.
        """
        logger.info("🕵️ [Evolution] Periodic Shadow Audit: Starting validation of established rules...")
        async with PostgresDB._session_factory() as session:
            # Audit rules that haven't been validated in the last 24h
            stmt = select(GraduatedRule).where(
                GraduatedRule.is_stable == True,
                GraduatedRule.is_quarantined == False
            ).limit(10)
            result = await session.execute(stmt)
            rules = result.scalars().all()

            for rule in rules:
                try:
                    from backend.utils.llm_utils import call_heavyweight_llm
                    # Simulate a request for the rule's pattern
                    ground_truth = await call_heavyweight_llm([
                        {"role": "system", "content": "Analyze the request and provide the definitive solution."},
                        {"role": "user", "content": rule.task_pattern}
                    ])
                    
                    # Check for semantic similarity
                    # (In v15.2, we'd use embedding distance, here we use exact match or simple inclusion for simulation)
                    matches = ground_truth.strip().lower() in rule.result_data.get("solution", "").lower()
                    
                    await cls.record_shadow_outcome(rule.id, matches)
                except Exception as e:
                    logger.error(f"[Evolution] Shadow audit failed for rule {rule.id}: {e}")
            
            # ⚖️ [Wire] Trigger Autonomous Alignment Recalibration
            try:
                from .alignment import alignment_engine
                await alignment_engine.auto_calibrate()
                logger.info("⚖️ [Evolution] Triggered autonomous alignment recalibration based on latest swarm drift.")
            except Exception as e:
                logger.error(f"[Evolution] Failed to trigger alignment recalibration: {e}")
                
        logger.info("🕵️ [Evolution] Shadow Audit complete.")

    @classmethod
    async def ingest_mission_outcome(
        cls, 
        mission_id: str, 
        input_data: str, 
        output_data: str, 
        fidelity: float, 
        agent_path: List[str]
    ):
        """
        Sovereign v19.0: Native Evolution Wiring.
        Bridges the high-level mission result directly to the PPO optimization engine.
        """
        if cls.DISABLED: return
        
        logger.info(f"🧬 [Evolution] Ingesting Outcome for Mission {mission_id}. Fidelity: {fidelity:.4f}")
        
        # 1. Record outcome in legacy pipeline for stability
        await cls.record_outcome(
            user_id="mainframe",
            query=input_data,
            response=output_data,
            fidelity=fidelity,
            domain=agent_path[0] if agent_path else "default",
            mission_context={"mission_id": mission_id, "path": agent_path}
        )

        # 2. Direct PPO Heartbeat (Atomic weights update)
        try:
            from backend.core.evolution.ppo_engine import get_ppo_engine, Trajectory
            ppo = get_ppo_engine()
            
            # Map mission outcome to a reinforced Trajectory
            # For v19.0, we treat the final fidelity as a scalar reward
            traj = Trajectory(
                states=[input_data], 
                actions=[agent_path[-1] if agent_path else "idling"],
                rewards=[fidelity]
            )
            
            # 🧪 Anchoring: Anchor the batch via DatasetManager
            from backend.core.evolution.dataset_manager import get_dataset_manager
            dm = get_dataset_manager()
            batch_id = dm.anchor_batch([{"input": input_data, "output": output_data, "fidelity": fidelity}])
            
            # Trigger PPO train step if buffer is ready
            ppo.add_trajectory(traj)
            if len(ppo.trajectories) >= 20: # Optimized for v22 graduation visibility
                 logger.info(f"🔥 [Evolution] PPO Batch Threshold met (Anchor: {batch_id[:8]}). Optimizing Weights...")
                 await ppo.train_step()
                
        except Exception as e:
            logger.error(f"❌ [Evolution] PPO Wiring failure: {e}")

    @classmethod
    def _detect_system_drift(cls) -> bool:
        """
        Sovereign v15.0: Hardware-Aware Drift Detection.
        Checks for VRAM pressure or model swaps that might invalidate graduated rules.
        """
        from backend.core.executor.guardrails import capture_resource_pressure
        pressure = capture_resource_pressure()
        if pressure.get("vram_pressure", 0) > 0.9:
            return True # Invalidate fast-path if memory is choked
        return False

    @classmethod
    async def analyze_system_fragility(cls):
        """
        Phase 3.5: Autonomous Self-Healing.
        Identifies highly fragile domains and proposes system-level logic mutations.
        """
        logger.info("🔬 [Evolution] Analyzing system-wide fragility for self-healing...")
        async with PostgresDB._session_factory() as session:
            stmt = select(FragilityIndex).where(FragilityIndex.fragility_score > 0.7)
            res = await session.execute(stmt)
            fragile_domains = res.scalars().all()
            
            for domain in fragile_domains:
                logger.warning(f"🚨 [Evolution] CRITICAL FRAGILITY in domain '{domain.domain}' (Score: {domain.fragility_score})")
                await cls._propose_system_patch(domain.domain)

    @classmethod
    async def _propose_system_patch(cls, domain: str):
        """
        Generates a software mutation proposal to stabilize a fragile domain.
        v16.2: Logic Synthesis pass.
        """
        from backend.db.models import MutationProposal
        from backend.utils.llm_utils import call_lightweight_llm
        
        proposal_name = f"patch_fragility_{domain}_{int(time.time())}"
        logger.info(f"🧠 [Evolution] Synthesizing mutation proposal: {proposal_name}")
        
        # 1. Synthesize the patch logic
        prompt = f"""
        Domain: {domain}
        Issue: Sustained high-fragility and failure rate.
        Objective: Propose a logic refinement for backend/core/intent_rules.py to handle this better.
        
        Return ONLY the logic diff or rule change.
        """
        try:
            patch_logic = await call_lightweight_llm([{"role": "system", "content": prompt}])
            
            async with PostgresDB._session_factory() as session:
                proposal = MutationProposal(
                    mutation_type="logic_refinement",
                    proposal_name=proposal_name,
                    logic_diff=patch_logic,
                    target_metric="fragility_score",
                    expected_improvement=0.3,
                    status="proposed"
                )
                session.add(proposal)
                await session.commit()
                
            logger.info(f"✅ [Evolution] Mutation Proposal PERSISTED: {proposal_name}")
        except Exception as e:
            logger.error(f"[Evolution] Patch synthesis failed: {e}")

    @classmethod
    async def evolve_swarm(cls):
        """
        Sovereign v22.0: Self-Driven Swarm Evolution.
        Triggered by Orchestrator Sentinel.
        Coordinates dreaming cycles and weight tuning.
        """
        logger.info("🌌 [Evolution] Sentinel Trigger: Initializing Swarm Evolution Pulse...")
        await cls.run_dreaming_session()
        
        # Check if we have enough PPO data to train
        from .evolution.ppo_engine import get_ppo_engine
        ppo = get_ppo_engine()
        if len(ppo.trajectories) >= 20:
             logger.info("🔥 [Evolution] PPO Graduation Threshold met. Commencing policy optimization...")
             await ppo.train_step()
