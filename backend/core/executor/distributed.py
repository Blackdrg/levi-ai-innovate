import os
import json
import asyncio
import logging
import uuid
import redis.asyncio as redis
from typing import List, Dict, Any, Optional
from ..task_graph import TaskNode
from ..orchestrator_types import ToolResult
from . import GraphExecutor
from ..cloud_fallback import CloudFallbackProxy
from .streams import StreamManager
from ..dcn.resource_manager import ResourceManager
from ..v13.vram_guard import VRAMGuard
from ..v13.dynamic_batching import DynamicBatcher

logger = logging.getLogger(__name__)

TASK_QUEUE = "dcn:task_queue"
# TTL for results to prevent Redis bloat
RESULT_TTL = 3600 

class DistributedGraphExecutor:
    """
    Sovereign Distributed Executor v2.0.
    Handles multi-node task distribution and task-stealing logic.
    """
    def __init__(self, r: Optional[redis.Redis] = None):
        self.r = r or redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        self.node_id = os.getenv("DCN_NODE_ID", f"node-{uuid.uuid4().hex[:8]}")
        self.node_role = os.getenv("NODE_ROLE", "worker")
        self.node_weight = int(os.getenv("NODE_WEIGHT", "4"))
        
        self.streams = StreamManager()
        self.resource_mgr = ResourceManager()
        self.vram_guard = VRAMGuard()
        
        self.executor_logic = GraphExecutor()
        self.cloud_proxy = CloudFallbackProxy()
        self.batcher = DynamicBatcher()
        self.is_running = False
        
        # v2.1 Specialized Streams
        self.task_streams = [TASK_STREAM]
        if os.getenv("SD_ENABLED", "false").lower() == "true":
            self.task_streams.append("dcn:studio_stream")
            logger.info(f"🎨 [DCN Worker] Node {self.node_id} registered with STUDIO capability.")

    async def enqueue_wave(self, mission_id: str, wave: List[TaskNode], perception: Dict[str, Any], previous_results: Dict[str, Any]):
        """
        Pushes a wave of tasks to the shared Redis queue.
        Each task is packaged with its required context.
        """
        logger.info(f"[DCN Executor] Enqueuing wave of {len(wave)} tasks for mission {mission_id}")
        
        # Security Hardening: Coordinator-Only Enqueueing
        if self.node_role != "coordinator":
            logger.error(f"[DCN Security] Deployment Error: Node {self.node_id} (Role: {self.node_role}) attempted to enqueue wave. Multi-node RBAC breach blocked.")
            return False

        # v2.0 Stream Orchestration
        await self.streams.setup_groups()
        
        for node in wave:
            # 📊 Audit Point 68: Intelligent Targeting (v13.1 Tier-Aware)
            model_tier = getattr(node, 'tier', "L2")
            target_node_hint = await self.resource_mgr.find_optimal_node(model_tier)
            
            task_pkg = {
                "mission_id": mission_id,
                "node_id": node.id,
                "node_data": node.dict(),
                "perception": perception,
                "previous_results": previous_results,
                "enqueued_at": asyncio.get_event_loop().time(),
                "priority": perception.get("priority", "medium"),
                "target_node": target_node_hint,
                "model_tier": model_tier
            }
            await self.streams.enqueue_task(task_pkg, priority=task_pkg["priority"])
            logger.info(f"[DCN] Task {node.id} dispatched to cluster (Hint: {target_node_hint})")
        return True

    async def worker_loop(self):
        """
        Participation loop: Pulls and executes tasks from the shared queue.
        Implements Task Stealing: If local node is busy, task is pushed back for others.
        """
        self.is_running = True
        logger.info(f"[DCN Worker] Node {self.node_id} participating in swarm.")
        await self.streams.setup_groups()

        while self.is_running:
            try:
                # v2.1: Multi-stream Pull
                tasks = []
                for stream in self.task_streams:
                    # Switch stream context
                    self.streams.stream_name = stream
                    stream_tasks = await self.streams.pull_tasks(self.node_id, count=1)
                    tasks.extend([(stream, t) for t in stream_tasks])
                
                if not tasks:
                    if self.node_role == "coordinator":
                        await self.streams.auto_claim_abandoned()
                    await asyncio.sleep(1)
                    continue

                for stream_name, (msg_id, task_pkg, delivery_count) in tasks:
                    mission_id = task_pkg["mission_id"]
                    node_id = task_pkg["node_id"]
                    task_type = task_pkg.get("type", "cognitive")
                    model_tier = task_pkg.get("model_tier", "L2")
                    
                    # 🚀 Audit Point: Delivery Cap (Backoff logic)
                    if delivery_count > 1:
                        wait_sec = min(30, 2 ** delivery_count)
                        logger.info(f"⏳ [DCN Worker] Retry detected ({delivery_count}). Backing off {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                    
                    # 🛡️ 2. Distributed Resource Guard (VRAM)
                    # v2.1: Specialized Handler Selection
                    if task_type == "studio_generate":
                        await self._process_studio_task(msg_id, task_pkg)
                        continue

                    model_tier = task_pkg.get("model_tier", "L2")
                    if not await self.vram_guard.check_capacity(model_tier):
                        logger.warning(f"[DCN Worker] VRAM Pressure! Node {self.node_id} skipping {node_id}")
                        await asyncio.sleep(1) 
                        continue

                    # 3. Target Node Hint (Optional optimization)
                    target = task_pkg.get("target_node")
                    if target and target != self.node_id:
                        # Allow other nodes a chance if we are NOT the target, 
                        # but only if wait time is low
                        enqueued_at = task_pkg.get("enqueued_at", 0)
                        if (asyncio.get_event_loop().time() - enqueued_at) < 5:
                            logger.debug(f"[DCN Worker] {self.node_id} passing on non-target task {node_id}")
                            continue

                    # Execute task
                    asyncio.create_task(self._process_task_v2(msg_id, task_pkg))

            except Exception as e:
                logger.error(f"[DCN Worker] Loop error: {e}")
                await asyncio.sleep(1)

    async def _process_task_v2(self, msg_id: str, task_pkg: Dict[str, Any]):
        """Executes a task and ACKs the Redis Stream message."""
        mission_id = task_pkg["mission_id"]
        node_id = task_pkg["node_id"]
        model_tier = task_pkg.get("model_tier", "L2")
        
        try:
            logger.info(f"[DCN Worker] Processing {node_id} ({model_tier}) by {self.node_id}")
            node = TaskNode(**task_pkg["node_data"])
            
            # Bridge to local executor logic (Optimized via Batcher)
            prev_results_raw = task_pkg.get("previous_results", {})
            previous_results = {k: ToolResult(**v) if isinstance(v, dict) else v for k, v in prev_results_raw.items()}
            
            result = await self.batcher.execute_batched(
                model_tier,
                (node, previous_results, task_pkg["perception"]),
                handler=lambda p: self.executor_logic._execute_node(*p)
            )
            
            # 🏁 Persistence & Feedback
            result_key = f"dcn:mission:{mission_id}:result:{node_id}"
            await self.r.setex(result_key, RESULT_TTL, json.dumps(result.dict()))
            await self.r.publish(f"dcn:mission:{mission_id}:events", json.dumps({"event": "node_complete", "node_id": node_id}))
            
            # 🎖️ ACK message
            await self.streams.acknowledge_task(msg_id)
            logger.info(f"[DCN Worker] Task {node_id} CRYSTALLIZED and ACKed.")
            
        except Exception as e:
            logger.error(f"[DCN Worker] Execution Drift in v2: {e}")
            # Do NOT ACK - let it be claimed by others or retry later
            await self.r.publish(f"dcn:mission:{mission_id}:events", json.dumps({"event": "node_failed", "node_id": node_id, "error": str(e)}))

    async def _process_studio_task(self, msg_id: str, task_pkg: Dict[str, Any]):
        """Handles creative generation tasks using the local Studio engine."""
        mission_id = task_pkg["mission_id"]
        payload = task_pkg.get("payload", {})
        
        try:
            logger.info(f"🎨 [DCN Studio] Synthesising image for mission {mission_id}...")
            from backend.engines.studio.sd_logic import StudioGenerator
            studio = StudioGenerator()
            
            # Force local generation since this is a Studio-capable worker
            # NOTE: We use the internal _methods to avoid re-offloading to DCN
            img_buf = await studio._generate_via_comfyui(
                payload["prompt"], "", (payload["width"], payload["height"])
            )
            
            if not img_buf:
                img_buf = await studio._generate_via_sdwebui(
                    payload["prompt"], "", (payload["width"], payload["height"])
                )

            if img_buf:
                import base64
                img_b64 = base64.b64encode(img_buf.getvalue()).decode()
                
                # Store in Redis result key
                res_key = f"dcn:mission:{mission_id}:result"
                await self.r.setex(res_key, RESULT_TTL, img_b64)
                
                # Acknowledge and notify
                self.streams.stream_name = "dcn:studio_stream"
                await self.streams.acknowledge_task(msg_id)
                await self.r.publish(f"dcn:mission:{mission_id}:events", json.dumps({"event": "node_complete"}))
                logger.info(f"🎨 [DCN Studio] Mission {mission_id} Complete. Pulse sent.")
            else:
                logger.error(f"🎨 [DCN Studio] Mission {mission_id} failed on this node.")
                
        except Exception as e:
            logger.error(f"💥 [DCN Studio] Critical crash: {e}")

    async def _process_cloud_fallback(self, task_pkg: Dict[str, Any]):
        """
        Executes a task using CloudFallbackProxy with multi-tier budget enforcement.
        Prevents sovereign leakage while ensuring mission graduation.
        """
        mission_id = task_pkg["mission_id"]
        node_id = task_pkg["node_id"]
        session_id = task_pkg.get("perception", {}).get("session_id", "global")
        
        try:
            # 1. Budget Gates
            mission_budget_key = f"budget:cloud:mission:{mission_id}"
            session_budget_key = f"budget:cloud:session:{session_id}"
            
            m_spent = int(await self.r.get(mission_budget_key) or 0)
            s_spent = int(await self.r.get(session_budget_key) or 0)
            
            # Limits: 5 cloud calls per mission, 20 per session (Default Hardening)
            if m_spent >= 5 or s_spent >= 20:
                logger.error(f"🛑 [Budget] Cloud Exhaustion for {mission_id}. Session: {s_spent}/20. Aborting.")
                await self.r.publish(f"dcn:mission:{mission_id}:events", json.dumps({"event": "node_failed", "node_id": node_id, "error": "Cloud Budget Exhausted"}))
                return

            logger.info(f"☁️ [DCN Cloud] Scaling {node_id} to Overflow Buffer (Mission: {m_spent+1}/5)")
            
            # 2. Execution
            perception = task_pkg["perception"]
            messages = [{"role": "user", "content": perception.get("input", "Synchronous overflow")}]
            
            res_message = await self.cloud_proxy.generate_overflow(messages)
            
            if res_message:
                # 3. Success & Accounting
                await self.r.incr(mission_budget_key)
                await self.r.expire(mission_budget_key, 3600)
                await self.r.incr(session_budget_key)
                await self.r.expire(session_budget_key, 86400)

                result = ToolResult(
                    success=True,
                    message=res_message,
                    agent="CloudFallback",
                    latency_ms=1500
                )
                
                result_key = f"dcn:mission:{mission_id}:result:{node_id}"
                await self.r.setex(result_key, RESULT_TTL, json.dumps(result.dict()))
                await self.r.publish(f"dcn:mission:{mission_id}:events", json.dumps({"event": "node_complete", "node_id": node_id}))
            else:
                logger.error(f"☁️ [DCN Cloud] Provider failure for {node_id}.")
                # Do NOT ACK - let it re-enqueue for local retry or eventually DLQ
                
        except Exception as e:
            logger.error(f"💥 [DCN Cloud] Execution error: {e}")

    def stop(self):
        self.is_running = False
