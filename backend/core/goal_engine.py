import logging
import uuid
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.db.models import Goal, Mission
from backend.db.postgres import PostgresDB
from backend.services.brain_service import brain_service
from backend.core.model_router import ModelRouter
from backend.core.execution_state import MissionState
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
        logger.info("🛰️ [GoalEngine] Autonomous Spawner active.")

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
            
            # 1. Fetch LLM Policy for decomposition
            model = ModelRouter.get_model_for_tier("L3", complexity=0.8)
            
            prompt = f"""
            ### SOVEREIGN OBJECTIVE DECOMPOSITION ###
            Goal ID: {goal.goal_id}
            Objective: {goal.objective}
            
            Break this long-term objective into a list of nested SUB-GOALS and immediate MISSIONS.
            Sub-goals are high-level strategic steps.
            Missions are concrete, actionable tasks for the Orchestrator to execute NOW.
            
            Output strictly as JSON:
            {{
                "sub_goals": [{{ "objective": "...", "priority": 1.5 }}],
                "missions": [{{ "objective": "...", "intent_type": "search/code/etc" }}],
                "reasoning": "Brief technical logic"
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
        """
        while self._is_running:
            try:
                await self._spawn_pending_missions()
            except Exception as e:
                logger.error(f"[GoalEngine] AutoSpawner error: {e}")
            await asyncio.sleep(60) # Pulse every minute

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
            
            completed = len([m for m in missions if m.status == "complete"])
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
