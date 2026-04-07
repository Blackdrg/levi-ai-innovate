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
        self.node_id = os.getenv("DCN_NODE_ID", "node-alpha")
        self.node_role = os.getenv("NODE_ROLE", "worker")
        self.node_weight = int(os.getenv("NODE_WEIGHT", "4")) # Default to 4 slots (RC1 standard)
        self.semaphore = asyncio.Semaphore(self.node_weight)
        self.executor_logic = GraphExecutor() # Reuse node execution logic
        self.is_running = False

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

        for node in wave:
            task_pkg = {
                "mission_id": mission_id,
                "node_id": node.id,
                "node_data": node.dict(),
                "perception": perception,
                "previous_results": previous_results,
                "enqueued_at": asyncio.get_event_loop().time()
            }
            await self.r.lpush(TASK_QUEUE, json.dumps(task_pkg))
        return True

    async def worker_loop(self):
        """
        Participation loop: Pulls and executes tasks from the shared queue.
        Implements Task Stealing: If local node is busy, task is pushed back for others.
        """
        self.is_running = True
        logger.info(f"[DCN Worker] Node {self.node_id} participating in swarm.")

        while self.is_running:
            try:
                # Blocking pop from the task queue
                item = await self.r.blpop(TASK_QUEUE, timeout=5)
                if not item:
                    logger.debug(f"[DCN Worker] Node {self.node_id} is idle.")
                    continue

                _, task_json = item
                task_pkg = json.loads(task_json)
                mission_id = task_pkg["mission_id"]
                node_id = task_pkg["node_id"]

                # Task Stealing / Load Balancing Logic
                if self.semaphore.locked():
                    # Node is at capacity — put task back at the end of the queue for another node
                    logger.debug(f"[DCN Worker] Node busy. Stealing prevention: re-queueing {node_id}")
                    await self.r.rpush(TASK_QUEUE, task_json)
                    await asyncio.sleep(0.5) # Prevent tight-loop spinning
                    continue

                # Execute task in background to keep loop reactive
                asyncio.create_task(self._process_task(task_pkg))

            except redis.ConnectionError:
                logger.warning("[DCN Worker] Connection lost. Stalling...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[DCN Worker] Loop error: {e}")
                await asyncio.sleep(1)

    async def _process_task(self, task_pkg: Dict[str, Any]):
        """Executes a single task using the local executor logic and publishes the result."""
        mission_id = task_pkg["mission_id"]
        node_id = task_pkg["node_id"]
        
        async with self.semaphore:
            logger.info(f"[DCN Worker] Executing task {node_id} for mission {mission_id}")
            
            try:
                node = TaskNode(**task_pkg["node_data"])
                # We need to bridge to GraphExecutor's _execute_node
                # Note: GraphExecutor._execute_node expects results as a Dict[str, ToolResult]
                previous_results_raw = task_pkg["previous_results"]
                previous_results = {k: ToolResult(**v) if isinstance(v, dict) else v for k, v in previous_results_raw.items()}
                
                result = await self.executor_logic._execute_node(
                    node, 
                    previous_results, 
                    task_pkg["perception"]
                )
                
                # Publish result back to Redis for the mission coordinator
                result_key = f"dcn:mission:{mission_id}:result:{node_id}"
                await self.r.setex(result_key, RESULT_TTL, json.dumps(result.dict()))
                
                # Notify completion (Pub/Sub or Stream can be used, but here we just use the key)
                await self.r.publish(f"dcn:mission:{mission_id}:events", json.dumps({"event": "node_complete", "node_id": node_id}))
                
                logger.info(f"[DCN Worker] Task {node_id} completed by {self.node_id}")

            except Exception as e:
                logger.exception(f"[DCN Worker] Task crached: {node_id} -> {e}")
                # Optional: Push failure event
                await self.r.publish(f"dcn:mission:{mission_id}:events", json.dumps({"event": "node_failed", "node_id": node_id, "error": str(e)}))

    def stop(self):
        self.is_running = False
