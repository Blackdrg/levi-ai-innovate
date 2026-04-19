import logging
import uuid
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from backend.db.models import Goal, Mission
from backend.db.postgres import PostgresDB
from backend.services.brain_service import brain_service
from backend.core.model_router import ModelRouter
from backend.core.execution_state import MissionState
from .identity import identity_system
import random
from sqlalchemy import select, update, insert

logger = logging.getLogger(__name__)

class GoalDecompositionResult(BaseModel):
    sub_goals: List[Dict[str, Any]] = []
    missions: List[Dict[str, Any]] = []
    reasoning: str = ""

class GoalEngine:
    """
    Sovereign v15.0: The Autonomous Goal Engine.
    Handles recursive decomposition of long-term objectives and manages 
    the lifecycle of sub-missions.
    """

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self._is_running = False
        self._spawner_task = None

    async def start(self):
        """Starts the background AutoSpawner."""
        if self._is_running: return
        self._is_running = True
        self._spawner_task = asyncio.create_task(self._autospawn_loop())
        
        # Start the Self-Healing Engine
        from .self_healing import self_healing
        await self_healing.start()
        
        logger.info("🛰️ [GoalEngine] Autonomous Spawner and Self-Healer active.")

    async def stop(self):
        """Stops the background AutoSpawner."""
        self._is_running = False
        if self._spawner_task:
            self._spawner_task.cancel()
            try: await self._spawner_task
            except asyncio.CancelledError: pass

    async def create_persistent_goal(self, user_id: str, objective: str, priority: float = 1.0, parent_goal_id: str = None) -> str:
        """Creates a new Goal in the database and triggers initial decomposition."""
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        
        async with await PostgresDB.get_session() as session:
            async with session.begin():
                new_goal = Goal(
                    goal_id=goal_id,
                    parent_goal_id=parent_goal_id,
                    user_id=user_id,
                    objective=objective,
                    priority=priority,
                    status="active"
                )
                session.add(new_goal)
        
        logger.info(f"[GoalEngine] Created goal: {goal_id} - {objective[:50]}...")
        
        # Trigger async decomposition
        asyncio.create_task(self.decompose_goal(goal_id))
        return goal_id

    async def decompose_goal(self, goal_id: str):
        """
        Recursive Goal Decomposition Wave.
        Uses L3/L4 models to break a Goal into SubGoals or actionable Missions.
        """
        async with await PostgresDB.get_session() as session:
            stmt = select(Goal).where(Goal.goal_id == goal_id)
            res = await session.execute(stmt)
            goal = res.scalar_one_or_none()
            if not goal: return

            logger.info(f"[GoalEngine] Decomposing objective: {goal.objective}")
            
            # 1. Fetch LLM Policy and Kernel Context
            model = ModelRouter.get_model_for_tier("L3", complexity=0.8)
            metrics = kernel.get_gpu_metrics()
            drivers = kernel.get_drivers()
            
            prompt = f"""
            ### SOVEREIGN OBJECTIVE DECOMPOSITION (v17.0-DYNAMIC) ###
            Goal ID: {goal.goal_id}
            Objective: {goal.objective}
            
            [SYSTEM CONTEXT - HARDWARE RESONANCE]
            - GPU VRAM: {metrics.get('vram_used_mb', 0)}/{metrics.get('vram_total_mb', 0)} MB
            - HAL Drivers: {drivers}
            - OS Status: v17.0.0-GA Sovereign
            
            Break this objective into nested SUB-GOALS and immediate MISSIONS.
            If resources (VRAM) are low, prioritize 'Optimization' or 'Cleanup' missions.
            If new HAL drivers are detected, generate 'Capability Probe' missions.
            
            Output strictly as JSON:
            {{
                "sub_goals": [{{ "objective": "...", "priority": 1.5 }}],
                "missions": [{{ "objective": "...", "intent_type": "search/code/recovery" }}],
                "reasoning": "Brief technical logic considering hardware state"
            }}
            """
            
            raw_resp = await brain_service.call_local_llm(prompt, model=model)
            try:
                # Basic JSON cleaning
                clean_json = raw_resp[raw_resp.find("{"):raw_resp.rfind("}")+1]
                data = json.loads(clean_json)
                
                # 2. Persist Sub-Goals (Recursion)
                for sg in data.get("sub_goals", []):
                    await self.create_persistent_goal(
                        user_id=goal.user_id,
                        objective=sg["objective"],
                        priority=sg.get("priority", goal.priority),
                        parent_goal_id=goal_id
                    )

                # 3. Persist immediate Missions (Spawning will happen in loop)
                for m in data.get("missions", []):
                    await self._register_mission_request(goal.user_id, goal_id, m)
                    
            except Exception as e:
                logger.error(f"[GoalEngine] Decomposition failure for {goal_id}: {e}")

    async def _register_mission_request(self, user_id: str, goal_id: str, mission_data: Dict[str, Any]):
        """Registers a mission that needs to be spawned."""
        async with await PostgresDB.get_session() as session:
            async with session.begin():
                new_mission = Mission(
                    mission_id=f"mission_{uuid.uuid4().hex[:8]}",
                    user_id=user_id,
                    goal_id=goal_id,
                    objective=mission_data["objective"],
                    intent_type=mission_data.get("intent_type", "general"),
                    status="pending"
                )
                session.add(new_mission)
        logger.info(f"[GoalEngine] Registered sub-mission request for Goal {goal_id}")

    async def _autospawn_loop(self):
        """
        Autonomous Spawner Loop.
        Finds 'pending' missions attached to active goals and dispatches them to the Orchestrator.
        Also triggers autonomous goal generation.
        """
        while self._is_running:
            try:
                # 1. Recalibrate Priorities
                await self._prioritize_goals()

                # 2. Spawn Missions
                await self._spawn_pending_missions()
                
                # 3. Sovereign v16.2: Autonomous Goal Generation
                await self._generate_autonomous_goals()
                
            except Exception as e:
                logger.error(f"[GoalEngine] AutoSpawner error: {e}")
            await asyncio.sleep(60) # Pulse every minute

    async def _generate_autonomous_goals(self):
        """
        Sovereign v16.2: Autonomous Goal Spawner.
        Generates NEW goals based on system identity, beliefs, and current state.
        Uses Personality Bias for 'Thinking' goals.
        """
        identity = await identity_system.get_identity()
        personality = identity["personality"]
        
        # Determine if we should generate a new goal based on 'Openness'
        if random.random() > (1.1 - personality.get("trait_openness", 0.5)):
            logger.info("🧠 [GoalEngine] Identity-driven Goal Generation Triggered.")
            
            # Using with_identity=True to inject the stable self into the goal generation
            prompt = """
            Strategic Reflection: Based on our core beliefs and traits, what should be our next major long-term objective?
            Focus on system hardening, knowledge expansion, or user assistance.
            
            Output JSON: {"objective": "...", "priority": 0.0 to 2.0, "reasoning": "..."}
            """
            
            try:
                res = await brain_service.call_local_llm(prompt, with_identity=True)
                data = json.loads(res.strip())
                
                await self.create_persistent_goal(
                    user_id="SYSTEM_AUTONOMOUS",
                    objective=data["objective"],
                    priority=data.get("priority", 1.0)
                )
                logger.info(f"✨ [GoalEngine] AUTONOMOUS STRATEGIC GOAL CREATED: {data['objective']}")
            except Exception as e:
                logger.error(f"[GoalEngine] Autonomous goal generation failed: {e}")

    async def _prioritize_goals(self):
        """
        Sovereign v16.2: Autonomous Priority Management.
        Adjusts priorities of active goals based on environmental urgency and identity traits.
        Formula: priority = base_priority * (1 + log(age_in_hours + 1)) * (importance_weight)
        """
        async with await PostgresDB.get_session() as session:
            stmt = select(Goal).where(Goal.status == "active")
            res = await session.execute(stmt)
            goals = res.scalars().all()
            
            now = datetime.now(timezone.utc)
            for goal in goals:
                age_hours = (now - goal.created_at).total_seconds() / 3600
                
                # Time-based urgency boost (Logarithmic to avoid runaway priority)
                import math
                urgency_factor = 1.0 + math.log10(age_hours + 1)
                
                # Identity Bias (Personality determines how much we 'care' about older goals)
                identity = await identity_system.get_identity()
                conscientiousness = identity["personality"].get("trait_conscientiousness", 0.5)
                
                new_priority = goal.priority * urgency_factor * (0.8 + conscientiousness * 0.4)
                goal.priority = min(10.0, round(new_priority, 2))
                
            await session.commit()
            logger.info(f"📊 [GoalEngine] priorities recalibrated for {len(goals)} active objectives.")

    async def _spawn_pending_missions(self):
        """Dispatches pending missions to the Orchestrator."""
        if not self.orchestrator: return

        async with await PostgresDB.get_session() as session:
            # Join with Goal to ensure parent is still active
            stmt = select(Mission).join(Goal).where(
                Mission.status == "pending",
                Goal.status == "active"
            ).limit(2) # Throttle spawning rate
            
            res = await session.execute(stmt)
            pending = res.scalars().all()
            
            for m in pending:
                logger.info(f"[GoalEngine] 🚀 Autonomously spawning mission: {m.mission_id} for Goal {m.goal_id}")
                
                # Send notification (Placeholder for v15.0 Notification system)
                # SovereignBroadcaster.publish("AUTONOMOUS_SPAWN", {"goal_id": m.goal_id, "mission_id": m.mission_id})
                
                # Update status to avoid double-spawn
                m.status = "executing"
                await session.commit()
                
                # Dispatch to Orchestrator
                asyncio.create_task(self.orchestrator.handle_mission_request(
                    request_id=m.mission_id,
                    user_id=m.user_id,
                    objective=m.objective,
                    goal_id=m.goal_id
                ))

    async def update_goal_progress(self, goal_id: str):
        """Calculates and updates goal progress based on linked mission status."""
        async with await PostgresDB.get_session() as session:
            # Count missions and sub-goals
            missions_stmt = select(Mission).where(Mission.goal_id == goal_id)
            subgoals_stmt = select(Goal).where(Goal.parent_goal_id == goal_id)
            
            m_res = await session.execute(missions_stmt)
            sg_res = await session.execute(subgoals_stmt)
            
            missions = m_res.scalars().all()
            subgoals = sg_res.scalars().all()
            
            total = len(missions) + len(subgoals)
            if total == 0: return
            
            completed = len([m for m in missions if m.status.lower() in ["complete", "completed"]])
            completed += sum([sg.progress for sg in subgoals])
            
            progress = completed / total
            
            await session.execute(
                update(Goal).where(Goal.goal_id == goal_id).values(
                    progress=progress,
                    status="achieved" if progress >= 1.0 else "active"
                )
            )
            await session.commit()
            
            # Recurse up to parent
            res = await session.execute(select(Goal.parent_goal_id).where(Goal.goal_id == goal_id))
            parent_id = res.scalar()
            if parent_id:
                await self.update_goal_progress(parent_id)

goal_engine = GoalEngine()
