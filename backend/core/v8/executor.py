"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
Mission Executor: Bridges the task graph to the parallel agent swarm.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
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

# Sovereign OS v14.0.0: Hardware-Aware VRAM Resource Pool
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
                 from ..orchestrator_types import ToolResult as BrainToolResult
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
        
        # 🛡️ Phase 2: Predictive CU Costing (Warn then Block)
        estimated_total_cu = graph.estimate_graph_cost()
        logger.info(f"📊 [Phase 2] Mission Cost Prediction: {estimated_total_cu:.1f} CU (Ceiling: {ceiling} CU)")
        
        if estimated_total_cu > ceiling:
            severity = "CRITICAL" if estimated_total_cu > (ceiling * 1.5) else "WARNING"
            logger.warning(f"⚠️ [Phase 2] Prediction Violation: {estimated_total_cu:.1f} CU exceeds {ceiling} CU limit. Status: {severity}")
            
            broadcast_mission_event(user_id, "cost_prediction_alert", {
                "estimated": estimated_total_cu,
                "ceiling": ceiling,
                "severity": severity
            })
            
            # Policy: "First warn then block"
            # If critical (e.g. 50% over limit), we block immediately. Otherwise, we warn.
            if severity == "CRITICAL":
                logger.error(f"🚫 [Phase 2] Mission BLOCKED: Predicted cost {estimated_total_cu:.1f} CU is too high.")
                MISSION_ABORTED.inc()
                return []
        
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
                    from backend.utils.runtime_tasks import create_tracked_task
                    create_tracked_task(self._checkpoint(user_id, session_id, perception.get("mission_id"), graph), name=f"mission-checkpoint-{session_id}")
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
        
        # 🛠️ Adaptive Backpressure: Multi-Tier Degradation (v14.1.0)
        requested_tier = getattr(node, 'tier', "L3" if agent_name in ["code_agent", "research_agent"] else "L2")
        target_tier = await GLOBAL_VRAM_GUARD.get_recommended_tier(requested_tier)
        
        if target_tier != requested_tier:
             logger.warning(f"🔋 [Backpressure] Degrading {node.id}: {requested_tier} -> {target_tier}")
             if target_tier == "MENTAL_COMPRESSION":
                 agent_name = "mental_compressor"
                 merged_params["original_agent"] = node.agent
                 merged_params["reason"] = "resource_saturation"
             else:
                 # Pass the downgraded tier to the agent/LLM config
                 merged_params["forced_model_tier"] = target_tier
                 merged_params["reason"] = "vram_backpressure"
             
             vram_needed = GLOBAL_VRAM_GUARD.get_vram_requirement(target_tier if target_tier != "MENTAL_COMPRESSION" else "L1")
        else:
             vram_needed = GLOBAL_VRAM_GUARD.get_vram_requirement(requested_tier)
        
        try:
            # 1.5. HITL: Human Approval Gate (v13.0)
            if agent_name == "human_approval":
                return await self._handle_human_approval(node, merged_params, perception)

            # 2. Secure Call via Global VRAM Pool & AI Service Breaker
            if GLOBAL_VRAM_POOL:
                # v14.0: Burst Mode allowed for L3/L4 tiers or high-load
                is_local = await GLOBAL_VRAM_POOL.acquire(vram_needed, burst_mode=(target_tier in ["L3", "L4"]))
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
        LeviBrain v14.1.0: Advanced Compensation & Rollback Engine.
        Covers the top 5 production failure modes.
        """
        from .critic import ReflectionEngine
        critic = ReflectionEngine()
        
        user_id = perception.get("user_id")
        session_id = perception.get("session_id")
        mission_id = perception.get("mission_id")
        
        logger.info(f"[Compensation] Analyzing failure for node '{node.id}' in mission {mission_id}")
        
        # 1. Qualitative Evaluation & Failure Classification
        evaluation = await critic.evaluate_failure(node, result, perception)
        failure_mode = evaluation.get("failure_mode", "generic")
        
        # --- Handle Top 5 Failure Modes ---
        
        # A. Tool Failure mid-DAG (State Reversal)
        if failure_mode == "tool_failure":
            logger.warning(f"[Rollback] Triggering state reversal for tool {node.agent}")
            return await self._rollback_agent_state(node, result, perception)

        # B. DB Write Partial Commit (X-Transaction Cleanup)
        elif failure_mode == "db_partial_commit":
            logger.warning("[Rollback] Cleaning up partial database artifacts...")
            return await self._cleanup_db_artifacts(user_id, mission_id)

        # C. Neo4j Sync Failure (Resync Pulse)
        elif failure_mode == "graph_sync_failure":
            logger.warning("[Rollback] Graph sync drift detected. Initiating Neo4j resync pulse...")
            return await self._resync_graph_node(user_id, node)

        # D. Agent Timeout with Side-Effects
        elif failure_mode == "timeout_side_effect":
            logger.warning(f"[Rollback] Agent {node.agent} timed out. Scrubbing orphaned side-effects...")
            return await self._scrub_orphaned_tasks(mission_id, node.id)

        # E. Redis Eviction mid-mission (State Restoration)
        elif failure_mode == "redis_eviction":
            logger.warning("[Rollback] Redis cold-start pulse. Restoring mission state from Postgres...")
            return await self._restore_state_from_postgres(mission_id, graph)

        # 2. Traditional AI-Driven Recovery
        if evaluation.get("can_recover"):
            strategy = evaluation.get("strategy", "retry_with_params")
            if strategy == "local_fallback":
                 node.agent = "local_agent"
                 retry_res = await self._execute_node(node, graph.results, perception)
                 return retry_res.success
            elif strategy == "refined_parameters":
                 node.inputs.update(evaluation.get("remedy_inputs", {}))
                 retry_res = await self._execute_node(node, graph.results, perception)
                 return retry_res.success
                 
        return False

    async def _rollback_agent_state(self, node: Any, result: ToolResult, perception: Dict[str, Any]) -> bool:
        """Attempts to call a 'rollback' interface on the failed agent."""
        try:
            from ..tool_registry import get_tool
            agent_instance = get_tool(node.agent)
            if hasattr(agent_instance, "rollback"):
                await agent_instance.rollback(node.inputs, result.data, perception)
                return True
        except Exception as e:
            logger.error(f"[Rollback] Agent-level rollback failed for {node.agent}: {e}")
        return False

    async def _cleanup_db_artifacts(self, user_id: str, mission_id: str) -> bool:
        """Sovereign v14.1.0: Mission State Compensation."""
        try:
            from backend.db.postgres_db import get_write_session
            from sqlalchemy import text
            
            async with get_write_session() as session:
                # Mark mission as COMPENSATED in SQL to stop further downstream artifacts
                await session.execute(
                    text("UPDATE missions SET state = 'COMPENSATED', metadata = jsonb_set(metadata, '{compensated_at}', :ts) WHERE id = :mid"),
                    {"mid": mission_id, "ts": f'"{datetime.now(timezone.utc).isoformat()}"'}
                )
                await session.commit()
            
            logger.info(f"[Compensation] Mission {mission_id} marked as COMPENSATED in Postgres.")
            return True
        except Exception as e:
            logger.error(f"[Compensation] DB cleanup failed: {e}")
            return False

    async def _resync_graph_node(self, user_id: str, node: Any) -> bool:
        """Force-syncs the relevant graph triplets for a node."""
        try:
            from backend.memory.graph_engine import GraphEngine
            ge = GraphEngine()
            # Re-extract triplets from inputs and re-upsert
            if hasattr(node, 'metadata') and "triplets" in node.metadata:
                for t in node.metadata["triplets"]:
                    await ge.upsert_triplet(
                        user_id=user_id, 
                        subject=t.get("subject"), 
                        relation=t.get("relation"), 
                        obj=t.get("object"), 
                        metadata=t.get("metadata")
                    )
            return True
        except Exception as e:
            logger.error(f"[Compensation] Graph resync failed: {e}")
            return False

    async def _scrub_orphaned_tasks(self, mission_id: str, node_id: str) -> bool:
        """Sovereign v14.1.0: Orphaned Task Scrubbing."""
        try:
            from backend.db.redis import r_async, HAS_REDIS
            if HAS_REDIS:
                # Clear session-specific trackers and inflight locks
                await r_async.delete(f"lock:node:{mission_id}:{node_id}")
                await r_async.hdel("mission:inflight_tasks", f"{mission_id}:{node_id}")
                
            logger.info(f"[Compensation] Scrubbed orphaned Redis state for {mission_id}:{node_id}")
            return True 
        except Exception as e:
            logger.error(f"[Compensation] Task scrubbing failed: {e}")
            return False

    async def _restore_state_from_postgres(self, mission_id: str, graph: Any) -> bool:
        """Restores the blackboard and results from Postgres if Redis data is evicted."""
        try:
            from backend.db.postgres_db import PostgresDB
            from backend.db.models import Mission
            from sqlalchemy import select
            async with PostgresDB._session_factory() as session:
                stmt = select(Mission).where(Mission.mission_id == mission_id)
                res = await session.execute(stmt)
                m = res.scalar_one_or_none()
                if m and m.payload:
                    # Update Redis with Postgres payload
                    from backend.db.redis import get_redis_client
                    client = get_redis_client()
                    if client:
                        client.setex(f"mission:{mission_id}", 3600, json.dumps(m.payload))
                    return True
            return False
        except: return False

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
