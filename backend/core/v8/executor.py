import asyncio
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from ..orchestrator_types import ToolResult
from ..tool_registry import call_tool
from backend.db.redis import r as redis_client, HAS_REDIS
from ...utils.network import ai_service_breaker

# Initialize Logger (v13.1 Resilience)
logger = logging.getLogger(__name__)

# V8. bridge: Telemetry & Swarm Intelligence
from backend.api.v8.telemetry import broadcast_mission_event
from backend.services.push_service import PushService
from backend.core.v8.blackboard import MissionBlackboard
from backend.core.v8.dreaming_task import DreamingTask
from backend.utils.audit import AuditLogger
from backend.core.v13.vram_guard import VRAMGuard, VRAMPool

from backend.config.system import CU_ABORT_THRESHOLD, CU_WARNING_PERCENT
from backend.utils.metrics import MISSION_COMPLETED, MISSION_ABORTED, MISSION_CU, GPU_SEMAPHORE_AVAILABLE

# Absolute Monolith v13: Hardware-Aware VRAM Resource Pool
# Replaced static Semaphore(4) with a model-aware unit allocator.
GLOBAL_VRAM_GUARD = VRAMGuard()
GLOBAL_VRAM_POOL = None 

# Compatibility Bridge for legacy telemetry
class SemaphoreAdapter:
    def __init__(self, pool): self.pool = pool
    @property
    def _value(self): return self.pool.available_mb if self.pool else 4
    def locked(self): return (self.pool.available_mb < 4096) if self.pool else False
    async def __aenter__(self): pass # Context support for legacy "async with"
    async def __aexit__(self, *args): pass
GLOBAL_GPU_SEMAPHORE = None 

class GraphExecutor:
    """
    LeviBrain v9.8.1: Robust Graph Executor.
    Implements topological parallel execution with 'Retry + Compensate' logic.
    """

    async def run(self, graph: Any, perception: Dict[str, Any], concurrency_limit: Optional[int] = None) -> List[ToolResult]:
        """
        LeviBrain v13.1: Orchestrates mission execution with Dynamic VRAM Pool Guarding.
        """
        global GLOBAL_VRAM_POOL, GLOBAL_GPU_SEMAPHORE
        if GLOBAL_VRAM_POOL is None:
            # 🛡️ Graduation Audit: Secure Hardware-Aware Pool Initialization
            slots = await GLOBAL_VRAM_GUARD.get_device_slots()
            total_vram_mb = sum(s["vram_total_mb"] for s in slots)
            
            # Initial Pool with 15% safety buffer
            usable_vram_mb = int(total_vram_mb * (1 - 0.15))
            GLOBAL_VRAM_POOL = VRAMPool(usable_vram_mb)
            GLOBAL_GPU_SEMAPHORE = SemaphoreAdapter(GLOBAL_VRAM_POOL)
            
            logger.info(f"[V13 Executor] Dynamic VRAM Pool Initialized: {usable_vram_mb}MB available across {len(slots)} devices.")

        concurrency_limit = concurrency_limit or 4 # Default if pool logic fails
        logger.info("[V9 Executor] Initiating Robust Topological Wave Execution...")
        user_id = perception.get("user_id", "default_user")
        
        # v9.8.1 Production Resilience: TaskSemaphore (Local concurrency limit)
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        async def _sem_execute(node):
            async with semaphore:
                return await self._execute_node_with_retry(node, graph, perception)

        # Swarm Intelligence: Initialize Blackboard
        session_id = perception.get("session_id", "default_session")
        mission_id = perception.get("mission_id")
        blackboard = MissionBlackboard(session_id)
        
        # 🛡️ v13.2 Resilience: Partial Mission Resume
        # Check if we are resuming an aborted mission
        start_wave = 1
        if mission_id:
             try:
                 from backend.db.postgres_db import PostgresDB
                 from sqlalchemy import select
                 from backend.db.models import AbortedMission
                 from backend.core.v8.brain import ToolResult as BrainToolResult
                 async with PostgresDB._session_factory() as session:
                     stmt = select(AbortedMission).where(AbortedMission.mission_id == mission_id)
                     res = await session.execute(stmt)
                     abortion = res.scalar_one_or_none()
                     if abortion:
                         logger.info(f"♻️ [Resilience] Resuming mission {mission_id} from wave {abortion.wave_index}.")
                         start_wave = abortion.wave_index
                         # Restore results to graph
                         for nid, raw_res in abortion.frozen_dag.get("results", {}).items():
                             graph.mark_complete(nid, BrainToolResult(**raw_res))
             except Exception as e:
                 logger.error(f"[Resilience] Failed to fetch abortion record for resume: {e}")

        if start_wave == 1:
            await blackboard.clear()
        
        # 📊 v13.1 Phase 5: CU Resource Tracking
        total_cu_consumed = 0
        warning_triggered = False
        ceiling = CU_ABORT_THRESHOLD
        warning_threshold = ceiling * CU_WARNING_PERCENT
        
        # Monitor Semaphore (v13.1 / Telemetry Bridge)
        GPU_SEMAPHORE_AVAILABLE.set(GLOBAL_GPU_SEMAPHORE._value)

        # 1. Topological Wave Execution Loop
        wave_index = 0
        while not graph.is_complete():
            wave_index += 1
            if wave_index < start_wave:
                continue # Skip already completed waves during resume
                
            executable_nodes = graph.get_ready_tasks()
            
            if not executable_nodes:
                if not graph.is_complete():
                    logger.error("[V9 Executor] Dependency deadlock or unrecoverable error.")
                break
            
            logger.info("[V9 Executor] Dispatching Wave (%d tasks): %s", len(executable_nodes), [n.id for n in executable_nodes])
            
            # 2. Parallel Execution with Semaphore-governed Wave
            tasks = [_sem_execute(n) for n in executable_nodes]
            wave_results = await asyncio.gather(*tasks)
            
            # Update Semaphore telemetry after wave
            GPU_SEMAPHORE_AVAILABLE.set(GLOBAL_GPU_SEMAPHORE._value)

            # 3. State Update & Failure Handling
            for n, res in zip(executable_nodes, wave_results):
                graph.mark_complete(n.id, res)
                
                # Hybrid Persistence: Checkpoint mission state after each task
                try:
                    asyncio.create_task(self._checkpoint(user_id, session_id, perception.get("mission_id"), graph))
                except: pass
                
                # Telemetry & CU Accounting
                cu_cost = res.cost_score if hasattr(res, 'cost_score') else 1
                total_cu_consumed += cu_cost
                
                # 🛑 CU Safety Gate: Warning (70%)
                if total_cu_consumed >= warning_threshold and not warning_triggered:
                    logger.warning("[V13.1 CU] Resource ceiling nearing: %d/%d CU (%.1f%%)", 
                                   total_cu_consumed, ceiling, (total_cu_consumed/ceiling)*100)
                    broadcast_mission_event(user_id, "cu_warning", {
                        "consumed": total_cu_consumed, 
                        "ceiling": ceiling,
                        "percentage": 70
                    })
                    warning_triggered = True
                
                # 💥 CU Safety Gate: Abort (100%)
                if total_cu_consumed > ceiling:
                    logger.error("[V13.1 CU] RESOURCE EXHAUSTION: Mission %s aborted at %d CU.", 
                                 perception.get("mission_id"), total_cu_consumed)
                    MISSION_ABORTED.inc()
                    MISSION_CU.observe(total_cu_consumed)
                    await self._notify_failure(user_id, n, graph, perception, wave_index)
                    return list(graph.results.values())

                broadcast_mission_event(user_id, "task_complete", {
                    "id": n.id, 
                    "success": res.success, 
                    "latency": res.latency_ms,
                    "agent": n.agent,
                    "cu_cost": cu_cost
                })
                
                # 4. 'Retry + Compensate' Logic for Critical Nodes
                if not res.success and n.critical:
                    logger.warning("[V9 Executor] Node %s failed. Triggering Compensation Pass...", n.id)
                    compensation_success = await self._compensate(n, res, graph, perception)
                    
                    if not compensation_success:
                        logger.error("[V9 Executor] Compensation failed for critical node %s. Aborting mission.", n.id)
                        await self._notify_failure(user_id, n, graph, perception, wave_index)
                        return list(graph.results.values())
                    else:
                        logger.info("[V9 Executor] Compensation successful for %s. Continuing graph...", n.id)

        # 5. Finalization & Dreaming
        if graph.is_complete():
            MISSION_COMPLETED.inc()
            MISSION_CU.observe(total_cu_consumed)
            broadcast_mission_event(user_id, "mission_complete", {"status": "success"})
            await blackboard.post_insight("executor", "Mission crystallized successfully.", tag="mission_summary")
            await DreamingTask.increment_and_check(user_id)
        else:
            MISSION_ABORTED.inc()
            MISSION_CU.observe(total_cu_consumed)

        return list(graph.results.values())

    async def _execute_node_with_retry(self, node: Any, graph: Any, perception: Dict[str, Any]) -> ToolResult:
        """Executes a node with exponential backoff retries."""
        max_retries = getattr(node, 'retry_count', 2)
        last_result = None
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info("[V9 Executor] Retrying node %s (Attempt %d/%d)...", node.id, attempt, max_retries)
                await asyncio.sleep(min(2 ** attempt, 10)) # Exponential backoff
            
            last_result = await self._execute_node(node, graph.results, perception)
            if last_result.success:
                return last_result
                
        return last_result

    async def _execute_node(self, node: Any, previous_results: Dict[str, ToolResult], perception: Dict[str, Any]) -> ToolResult:
        """Single node execution pass with VRAM Guarding."""
        agent_name = node.agent
        start_time = asyncio.get_event_loop().time()
        session_id = perception.get("session_id", "default_session")
        
        # 1. Resolve Inputs & Blackboard Context
        resolved_inputs = self._resolve_inputs(node, node.inputs, previous_results)
        blackboard_context = await MissionBlackboard.get_session_context(session_id)
        
        merged_params = {
            **perception.get("context", {}), 
            **resolved_inputs, 
            "input": perception.get("input"),
            "blackboard_context": blackboard_context,
            "session_id": session_id,
            "__node_metadata__": node.metadata
        }
        
        # 🛠️ Adaptive Backpressure: Mental Compression (v13.2)
        model_tier = getattr(node, 'tier', "L2")
        vram_needed = GLOBAL_VRAM_GUARD.get_vram_requirement(model_tier)
        
        # If GPU pool is saturated, we attempt 'Mental Compression' for non-critical nodes.
        if GLOBAL_VRAM_POOL and GLOBAL_VRAM_POOL.available_mb < vram_needed and not getattr(node, 'critical', False):
             logger.warning(f"🔋 [Backpressure] GPU Saturated for tier {model_tier}. Triggering Mental Compression for {node.id}")
             agent_name = "mental_compressor"
             merged_params["original_agent"] = node.agent
             merged_params["reason"] = "resource_exhaustion"
             vram_needed = GLOBAL_VRAM_GUARD.get_vram_requirement("L1") # 4GB for compressor
        
        try:
            # 1.5. HITL: Human Approval Gate (v13.0)
            if agent_name == "human_approval":
                return await self._handle_human_approval(node, merged_params, perception)

            # 2. Secure Call via Global VRAM Pool & AI Service Breaker
            if GLOBAL_VRAM_POOL:
                # v14.0: Burst Mode allowed for L3/L4 tiers or high-load
                is_local = await GLOBAL_VRAM_POOL.acquire(vram_needed, burst_mode=(model_tier in ["L3", "L4"]))
                if not is_local:
                    logger.warning(f"🚀 [Cloud Burst] Routing {agent_name} to cloud for mission {session_id}")
                    # Transition to Cloud Fallback
                    from backend.core.v13.cloud_burst_agent import CloudBurstAgent
                    burst_agent = CloudBurstAgent()
                    raw_res = await burst_agent.run(agent_name, merged_params, context=perception.get("context", {}))
                    return raw_res
            
            try:
                async with ai_service_breaker:
                    await AuditLogger.log_event(
                        event_type="AGENT",
                        action="Dispatch",
                        user_id=perception.get("user_id"),
                        resource_id=agent_name,
                        metadata={"mission_id": perception.get("mission_id"), "step_id": node.id, "vram_mb": vram_needed}
                    )
                    raw_res = await call_tool(
                        agent_name, 
                        merged_params, 
                        perception.get("context", {})
                    )
                    
                    await AuditLogger.log_event(
                        event_type="AGENT",
                        action="Result",
                        user_id=perception.get("user_id"),
                        resource_id=agent_name,
                        status="success" if getattr(raw_res, 'success', True) else "failed"
                    )

                # 3. Normalize Result
                if not hasattr(raw_res, 'success'):
                    from ..orchestrator_types import ToolResult as OrthoToolResult
                    result = OrthoToolResult(**raw_res) if isinstance(raw_res, dict) else OrthoToolResult(success=True, message=str(raw_res), agent=agent_name)
                else:
                    result = raw_res
                     
                result.latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                return result

            finally:
                if GLOBAL_VRAM_POOL:
                    await GLOBAL_VRAM_POOL.release(vram_needed)
            
        except Exception as e:
            logger.exception("[V9 Executor] Execution drift for %s: %s", agent_name, e)
            from ..orchestrator_types import ToolResult as OrthoToolResult
            return OrthoToolResult(success=False, error=str(e), agent=agent_name)

    async def _handle_human_approval(self, node: Any, params: Dict[str, Any], perception: Dict[str, Any]) -> ToolResult:
        """
        Suspends the mission and waits for a human approval signal via Redis.
        """
        user_id = perception.get("user_id")
        mission_id = perception.get("mission_id", str(uuid.uuid4()))
        node_id = node.id
        
        logger.info(f"[HITL] Node {node_id} requires human approval for mission {mission_id}")
        
        # 1. Register Pending Approval in Redis
        if HAS_REDIS:
            approval_key = f"hitl:approval:{mission_id}:{node_id}"
            redis_client.setex(approval_key, 3600, "pending") # 1 hour TTL
            
            # 2. Broadcast Event to UI
            broadcast_mission_event(user_id, "approval_required", {
                "mission_id": mission_id,
                "node_id": node_id,
                "prompt": params.get("prompt", "Approval required to proceed."),
                "context": params.get("context", {})
            })
            
            await AuditLogger.log_event(
                event_type="HITL",
                action="Suspended",
                user_id=user_id,
                resource_id=mission_id,
                metadata={"node_id": node_id, "prompt": params.get("prompt")}
            )
            
            # 3. Wait for Signal (Polling for simplicity in this version, can be optimized with PubSub)
            start_wait = asyncio.get_event_loop().time()
            timeout = 3600 # 1 hour
            
            while (asyncio.get_event_loop().time() - start_wait) < timeout:
                signal = redis_client.get(approval_key)
                if signal:
                    signal = signal.decode() if isinstance(signal, bytes) else signal
                    if signal == "approved":
                        logger.info(f"[HITL] Node {node_id} APPROVED.")
                        feedback = redis_client.get(f"{approval_key}:feedback")
                        return ToolResult(
                            success=True, 
                            message="Human Approved.", 
                            data={"feedback": feedback.decode() if feedback else ""},
                            agent="human_approval"
                        )
                    elif signal == "rejected":
                        logger.warning(f"[HITL] Node {node_id} REJECTED.")
                        return ToolResult(success=False, message="Human Rejected Mission.", agent="human_approval", retryable=False)
                
                await asyncio.sleep(2) # Poll every 2 seconds
                
        return ToolResult(success=False, message="HITL System Unavailable or Timeout.", agent="human_approval")

    async def _compensate(self, node: Any, result: ToolResult, graph: Any, perception: Dict[str, Any]) -> bool:
        """
        LeviBrain v9.8: Dynamic Compensation Pass.
        Attempts to fix a failed node by refined planning or local fallback.
        """
        from .critic import ReflectionEngine
        critic = ReflectionEngine()
        
        user_id = perception.get("user_id")
        logger.info("[Compensation] Analyzing failure for node: %s", node.id)
        
        # 1. Qualitative Evaluation
        evaluation = await critic.evaluate_failure(node, result, perception)
        
        if evaluation.get("can_recover"):
            strategy = evaluation.get("strategy", "retry_with_params")
            logger.info("[Compensation] Strategy identified: %s", strategy)
            
            if strategy == "local_fallback":
                 # Reroute to a local engine/agent for sovereignty
                 node.agent = "local_agent"
                 node.metadata["rerouted_from"] = node.agent
                 retry_res = await self._execute_node(node, graph.results, perception)
                 return retry_res.success
            
            elif strategy == "refined_parameters":
                 # Update inputs based on critic feedback
                 node.inputs.update(evaluation.get("remedy_inputs", {}))
                 retry_res = await self._execute_node(node, graph.results, perception)
                 return retry_res.success
                 
            elif strategy == "branch_patch":
                 # Refine the remaining graph (Evolutionary)
                 from .planner import DAGPlanner
                 planner = DAGPlanner()
                 new_subgraph = await planner.refine_plan(graph, evaluation, {}, perception)
                 # Merge or redirect? For simplicity, we just add the correction node
                 for n in new_subgraph.nodes:
                     n.dependencies = [node.id] # Force sequential dependency
                     graph.add_node(n)
                 return True # We consider this 'handled' by plan evolution
                 
        return False

    async def _notify_failure(self, user_id: str, node: Any, graph: Any = None, perception: Dict[str, Any] = None, wave_index: int = 0):
        push = PushService()
        mission_id = perception.get("mission_id") if perception else None
        
        # 🛡️ Resilience: Persist Aborted State for Replay (v13.1)
        if mission_id and graph:
            try:
                from backend.db.postgres_db import PostgresDB
                from backend.db.models import AbortedMission
                async with PostgresDB._session_factory() as session:
                    # Serialize Graph (assuming it has a to_dict or we serialize its core components)
                    frozen_dag = {
                        "nodes": [n.__dict__ for n in graph.nodes] if hasattr(graph, 'nodes') else [],
                        "results": {nid: res.__dict__ for nid, res in graph.results.items()}
                    }
                    
                    new_abort = AbortedMission(
                        mission_id=mission_id,
                        user_id=user_id,
                        frozen_dag=frozen_dag,
                        wave_index=wave_index,
                        error_node_id=node.id,
                        payload=perception
                    )
                    session.add(new_abort)
                    await session.commit()
                    logger.info(f"[Resilience] Mission {mission_id} persisted in AbortedMission ledger.")
            except Exception as e:
                logger.error(f"[Resilience] Failed to persist aborted mission {mission_id}: {e}")

        await push.send_critical_alert(
            user_id=user_id,
            title="Sovereign Mission Halt",
            message=f"Node '{node.id}' failed all compensation attempts.",
            data={"node": node.id, "mission_id": mission_id}
        )
        broadcast_mission_event(user_id, "mission_aborted", {"reason": f"Unrecoverable: {node.id}", "mission_id": mission_id})

    def _resolve_inputs(self, node: Any, inputs: Dict[str, Any], previous_results: Dict[str, ToolResult]) -> Dict[str, Any]:
        """Resolves template placeholders with swarm intelligence logic."""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                template = value.replace("{{", "").replace("}}", "")
                
                if template == "dependency_results":
                    resolved[key] = {tid: res.message for tid, res in previous_results.items() if tid in node.dependencies and res.success}
                elif template == "all_results":
                    resolved[key] = {tid: res.message for tid, res in previous_results.items() if res.success}
                else:
                    parts = template.split(".")
                    task_id = parts[0]
                    attr = parts[1] if len(parts) > 1 else "result"
                    
                    if task_id in previous_results:
                        res = previous_results[task_id]
                        if attr == "result": resolved[key] = res.message
                        elif attr == "data": resolved[key] = str(res.data)
                        else: resolved[key] = str(getattr(res, attr, ""))
                    else:
                        resolved[key] = value
            else:
                resolved[key] = value
        return resolved
    async def _checkpoint(self, user_id: str, session_id: str, mission_id: str, graph: Any):
        """
        LeviBrain v13 Hybrid Persistence Pass.
        Syncs current mission DAG state to Redis (active) and Postgres (recovery).
        """
        if not mission_id: return
        
        state = {
            "mission_id": mission_id,
            "user_id": user_id,
            "session_id": session_id,
            "status": "PROCESSING",
            "progress": graph.get_progress_percentage(),
            "completed_nodes": [nid for nid, res in graph.results.items() if res.success],
            "last_checkpoint": datetime.now(timezone.utc).isoformat()
        }
        
        # 1. Redis (Fast pulse for polling)
        if HAS_REDIS:
            try:
                redis_client.setex(f"mission:{mission_id}", 3600, json.dumps(state))
            except Exception as e:
                logger.error(f"[Checkpoint] Redis failure: {e}")

        # 2. Postgres (Hard persistence for graduation readiness)
        try:
             from backend.db.postgres import PostgresDB
             from backend.db.models import Mission
             async with PostgresDB._session_factory() as session:
                 from sqlalchemy import select
                 # Check if record exists
                 stmt = select(Mission).where(Mission.mission_id == mission_id)
                 res = await session.execute(stmt)
                 record = res.scalar_one_or_none()
                 
                 if record:
                     record.status = "PROCESSING"
                     record.payload = state
                     record.updated_at = datetime.now(timezone.utc)
                 else:
                     new_record = Mission(
                         mission_id=mission_id,
                         user_id=user_id,
                         status="PROCESSING",
                         objective="Async Mission", # Standard objective for async
                         payload=state
                     )
                     session.add(new_record)
                 await session.commit()
        except Exception as e:
             logger.error(f"[Checkpoint] Postgres failure: {e}")
