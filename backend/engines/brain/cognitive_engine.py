import asyncio
import logging
import uuid
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field

# Local imports
from backend.engines.brain.planner import BrainPlanner
from backend.engines.brain.orchestrator import distributed_orchestrator
from backend.redis_client import cache
from backend.db.postgres import PostgresDB
from backend.db.models import Mission, AbortedMission, Message
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

class MissionStep(BaseModel):
    step_id: str
    agent: str
    input: str
    depends_on: List[str] = []
    status: str = "pending" # pending, executing, completed, failed
    result: Optional[Any] = None
    retries: int = 0

class MissionState(BaseModel):
    mission_id: str
    user_id: str
    query: str
    status: str = "CREATED" # CREATED, PLANNING, EXECUTING, VALIDATING, REFINING, COMPLETED, FAILED
    plan: List[MissionStep] = []
    shared_context: Dict[str, Any] = {"facts": [], "results": [], "errors": []}
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def is_complete(self) -> bool:
        return self.status in ["COMPLETED", "FAILED"]

    def update_step(self, step_id: str, status: str, result: Any = None):
        for step in self.plan:
            if step.step_id == step_id:
                step.status = status
                if result:
                    step.result = result
                    self.shared_context["results"].append({"step_id": step_id, "agent": step.agent, "output": result})
        self.updated_at = time.time()
        self.save()

    def save(self):
        """Persist mission state to Redis and Postgres."""
        # 1. Redis for fast-path
        cache.set(f"mission:{self.mission_id}:state", self.model_dump_json(), ex=3600)
        
        # 2. Postgres for forensic truth (Background task)
        asyncio.create_task(self._save_to_postgres())

    async def _save_to_postgres(self):
        try:
            async with PostgresDB._session_factory() as session:
                mission = await session.get(Mission, self.mission_id)
                if not mission:
                    mission = Mission(
                        mission_id=self.mission_id,
                        user_id=self.user_id,
                        objective=self.query,
                        status=self.status,
                        payload=self.model_dump()
                    )
                    session.add(mission)
                else:
                    mission.status = self.status
                    mission.payload = self.model_dump()
                    mission.fidelity_score = self.shared_context.get("score", 0.0) / 100.0
                
                await session.commit()
        except Exception as e:
            logger.error(f"Postgres Mission Save Failed: {e}")

    async def persist_abortion(self, error_node: str):
        """Standardized v22.1 Resilience: Partial State Persistence."""
        try:
            async with PostgresDB._session_factory() as session:
                abort_record = AbortedMission(
                    mission_id=self.mission_id,
                    user_id=self.user_id,
                    frozen_dag=[step.model_dump() for step in self.plan],
                    error_node_id=error_node,
                    payload=self.shared_context
                )
                session.add(abort_record)
                
                # Update main mission status
                stmt = update(Mission).where(Mission.mission_id == self.mission_id).values(status="ABORTED")
                await session.execute(stmt)
                
                await session.commit()
                logger.warning(f"🛡️ [Resilience] Mission {self.mission_id} ABORTED. Partial state persisted to Postgres.")
        except Exception as e:
            logger.error(f"Persistence of mission abortion failed: {e}")

    @classmethod
    def load(cls, mission_id: str) -> Optional["MissionState"]:
        data = cache.get(f"mission:{mission_id}:state")
        if data:
            return cls.model_validate_json(data)
        return None

class CognitiveEngine:
    """
    Sovereign Cognitive Engine v22.1.
    A thinking loop that plans, executes, evaluates, and refines missions.
    """

    def __init__(self):
        self.planner = BrainPlanner()
        self.max_retries = 3

    async def run(self, user_id: str, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        mission_id = str(uuid.uuid4())
        state = MissionState(mission_id=mission_id, user_id=user_id, query=query)
        state.save()

        logger.info(f"🧠 [Brain] Mission initiated: {mission_id}")
        distributed_orchestrator.broadcast_mission_event(mission_id, "mission_started", {"query": query}, user_id=user_id)
        yield {"event": "mission_id", "data": mission_id}

        while not state.is_complete():
            # 1. PLANNING
            if state.status == "CREATED" or state.status == "REFINING":
                distributed_orchestrator.broadcast_mission_event(mission_id, "phase_started", {"phase": "PLANNING"}, user_id=user_id)
                yield {"event": "activity", "data": f"Architecting Strategy [Attempt {len(state.shared_context['errors']) + 1}]..."}
                state.status = "PLANNING"
                state.save()
                await self.plan_phase(state)
                yield {"event": "plan_ready", "data": {"steps": len(state.plan)}}

            # 2. EXECUTION
            if state.status == "PLANNING":
                distributed_orchestrator.broadcast_mission_event(mission_id, "phase_started", {"phase": "EXECUTING"}, user_id=user_id)
                yield {"event": "activity", "data": "Dispatching Sovereign Fleet..."}
                state.status = "EXECUTING"
                state.save()
                await self.execute_phase(state)

            # 3. EVALUATION
            if state.status == "EXECUTING":
                distributed_orchestrator.broadcast_mission_event(mission_id, "phase_started", {"phase": "VALIDATING"}, user_id=user_id)
                yield {"event": "activity", "data": "Evaluating Mission Fidelity..."}
                state.status = "VALIDATING"
                state.save()
                await self.evaluate_phase(state)
                yield {"event": "eval_result", "data": {"valid": state.shared_context["valid"], "score": state.shared_context.get("score")}}

            # 4. REFINEMENT / COMPLETION
            if state.status == "VALIDATING":
                if self.should_refine(state):
                    distributed_orchestrator.broadcast_mission_event(mission_id, "phase_started", {"phase": "REFINING"}, user_id=user_id)
                    yield {"event": "activity", "data": "Fidelity fail. Initiating rectification pulse..."}
                    state.status = "REFINING"
                    state.save()
                else:
                    state.status = "COMPLETED"
                    state.save()
                    distributed_orchestrator.broadcast_mission_event(mission_id, "mission_completed", {"status": "success"}, user_id=user_id)
                    yield {"event": "mission_complete", "data": {"mission_id": mission_id}}

            # 5. ABORTION (Failure)
            if state.status == "FAILED":
                await state.persist_abortion(error_node="CRITIC_OR_EXECUTOR")
                yield {"event": "error", "data": "Mission aborted after 3 failed fidelity cycles."}


        yield {"event": "final_state", "data": state.model_dump()}



    async def plan_phase(self, state: MissionState):
        """Break mission into steps (DAG) and assign agents."""
        logger.info(f"📋 [Brain] Planning phase for mission: {state.mission_id}")
        
        # In a real implementation, this would use an LLM to generate a dynamic DAG.
        # For MVW, we use the BrainPlanner templates.
        intent = await self.planner.classify_task(state.query)
        raw_plan = await self.planner.create_plan(state.query, intent)
        
        # Convert raw_plan to MissionStep objects
        steps = []
        for i, step in enumerate(raw_plan):
            steps.append(MissionStep(
                step_id=f"step_{i+1}",
                agent=step.get("agent_name", "cognition").upper(),
                input=step.get("params", {}).get("input", state.query),
                depends_on=[f"step_{d}" for d in ([step["depends_on"]] if "depends_on" in step else [])]
            ))
        
        state.plan = steps
        state.save()

    async def execute_phase(self, state: MissionState):
        """Run steps in the plan using DAG-aware parallel execution."""
        logger.info(f"🚀 [Brain] Parallel Execution phase for mission: {state.mission_id}")
        
        completed_steps = set()
        
        while len(completed_steps) < len(state.plan):
            # Identify "Ready" steps: pending AND all dependencies met
            ready_steps = [
                s for s in state.plan 
                if s.status == "pending" and (not s.depends_on or all(d in completed_steps for d in s.depends_on))
            ]
            
            if not ready_steps:
                # Check for deadlocks or failures
                if any(s.status == "failed" for s in state.plan):
                    logger.error("❌ [Brain] Execution halted due to step failure.")
                    break
                logger.warning("⚠️ [Brain] Potential deadlock in planning DAG.")
                break
            
            tasks = []
            for step in ready_steps:
                logger.info(f"📡 [Brain] Dispatching {step.agent} for {step.step_id}")
                tasks.append(self._execute_step(state, step))
            
            await asyncio.gather(*tasks)
            
            # Update completed set
            for s in ready_steps:
                if s.status in ["completed", "failed"]:
                    completed_steps.add(s.step_id)


    async def _execute_step(self, state: MissionState, step: MissionStep):
        # Update shared context for the agent
        step_input = step.input
        
        # Inject context from history and facts
        context_str = f"Facts: {state.shared_context['facts']}\n"
        if step.depends_on:
            prev_results = [s.result for s in state.plan if s.step_id in step.depends_on and s.result]
            if prev_results:
                context_str += f"Previous context: {prev_results}\n"
        
        full_input = f"{context_str}\nTask: {step_input}"

        # Exponential Backoff
        if step.retries > 0:
            backoff_time = 2 ** step.retries
            logger.info(f"⏳ [Brain] Backoff for {backoff_time}s before retry...")
            await asyncio.sleep(backoff_time)

        result = await distributed_orchestrator.execute_task(
            mission_id=state.mission_id,
            agent=step.agent,
            input_data=full_input,
            user_id=state.user_id
        )
        
        if result.get("status") == "completed":
            output = result.get("output")
            state.update_step(step.step_id, "completed", output)
            
            # Extract facts from output (Simple v1)
            # In a real system, another agent might do this.
            if "fact:" in output.lower():
                facts = [line.split("fact:")[1].strip() for line in output.split("\n") if "fact:" in line.lower()]
                state.shared_context["facts"].extend(facts)
        else:
            state.update_step(step.step_id, "failed", result.get("error"))
            if step.retries < self.max_retries:
                step.retries += 1
                logger.warning(f"🔄 [Brain] Retrying step {step.step_id} (Attempt {step.retries})")
                await self._execute_step(state, step)

    async def evaluate_phase(self, state: MissionState):
        """Validate output (Sentinel) with scoring."""
        logger.info(f"🔍 [Brain] Evaluation phase for mission: {state.mission_id}")
        
        # Consolidate results for evaluation
        all_results = "\n".join([f"{s.agent}: {s.result}" for s in state.plan if s.result])
        
        eval_result = await distributed_orchestrator.execute_task(
            mission_id=state.mission_id,
            agent="SENTINEL",
            input_data=(
                f"Evaluation Mission:\n"
                f"Original Query: {state.query}\n"
                f"Agent Outputs:\n{all_results}\n\n"
                f"SCORING CRITERIA: Accuracy, Security, Compliance.\n"
                f"Return format: SCORE: <0-100>, REASON: <why>, VALID: <TRUE/FALSE>"
            ),
            user_id=state.user_id
        )

        
        if eval_result.get("status") == "completed":
            output = eval_result.get("output", "")
            
            # Simple score extraction
            score = 0
            if "SCORE:" in output:
                try:
                    score = int(output.split("SCORE:")[1].split(",")[0].strip())
                except: pass
            
            valid = "VALID: TRUE" in output.upper() or score >= 80
            state.shared_context["score"] = score
            state.shared_context["valid"] = valid
            
            if not valid:
                logger.warning(f"⚠️ [Brain] Validation failed for {state.mission_id} (Score: {score})")
                state.shared_context["errors"].append(f"Validation failed: {output}")
        else:
            state.shared_context["valid"] = False

    def should_refine(self, state: MissionState) -> bool:
        # Refine if invalid and we haven't exhausted global retries
        if not state.shared_context.get("valid", True):
            if len(state.shared_context["errors"]) < self.max_retries:
                return True
            else:
                state.status = "FAILED"
                return False
        return False

    def final_output(self, state: MissionState) -> str:
        if state.status == "COMPLETED" and state.shared_context["results"]:
            return state.shared_context["results"][-1]["output"]
        return f"Mission ended with status: {state.status}. Context: {state.shared_context.get('errors', ['Unknown failure'])}"

cognitive_engine = CognitiveEngine()

