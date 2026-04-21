import asyncio
import logging
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator

# Local imports
from .planner import BrainPlanner
from .pipeline import FlowState, FlowPipeline
from backend.core.agent_registry import AgentRegistry
from backend.redis_client import cache
from backend.celery_app import celery_app

logger = logging.getLogger(__name__)

class DistributedOrchestrator:
    """
    Sovereign v22.1 Distributed Worker Proxy.
    Responsible for task dispatching to Celery workers and cross-node telemetry.
    Note: Mission lifecycle is governed by the Core Orchestrator (backend/core/orchestrator.py).
    """

    def __init__(self):
        self.queue = celery_app

    async def execute_task(self, mission_id: str, agent: str, input_data: str, user_id: str = "system") -> Dict[str, Any]:
        """Enqueue a task and wait for the result."""
        from backend.utils.tracing import traced_span
        
        async with traced_span("orchestrator.execute_task", mission_id=mission_id, agent=agent, user_id=user_id) as span:
            logger.info(f"📤 [Orchestrator] Enqueuing {agent} task for mission {mission_id}")
            
            # Notify via Pub/Sub
            self.broadcast_mission_event(mission_id, "task_queued", {"agent": agent})
            
            # 1. Enqueue via Celery
            task = self.queue.send_task(
                "backend.engines.brain.tasks.run_agent_task",
                args=[{"mission_id": mission_id, "agent": agent, "input": input_data, "user_id": user_id}],
                queue="default"
            )

            # 2. Polling for result
            max_wait = 180 # Increased to 3 minutes for complex tasks
            start_time = time.time()

            # Performance optimization for eager/local execution
            if hasattr(task, 'ready') and task.ready():
                logger.info(f"✅ [Brain] Task {task.id} completed immediately (Eager).")
                span.set_attribute("task.eager", True)
                return task.result if isinstance(task.result, dict) else {"status": "completed", "output": str(task.result)}
            
            while time.time() - start_time < max_wait:
                status = cache.get(f"task:{task.id}:status")
                if status == "executing":
                    self.broadcast_mission_event(mission_id, "task_executing", {"agent": agent, "task_id": task.id})
                
                if status in ["completed", "failed"]:
                    result_raw = cache.get(f"task:{task.id}:result")
                    if result_raw:
                        try:
                            import ast
                            result = ast.literal_eval(result_raw)
                            self.broadcast_mission_event(mission_id, "task_finished", {"agent": agent, "status": status})
                            span.set_attribute("task.status", status)
                            return result
                        except:
                            return {"status": status, "output": result_raw}
                
                await asyncio.sleep(1)
                
            span.set_attribute("task.status", "timeout")
            return {"status": "failed", "error": "Task timed out"}

    def broadcast_mission_event(self, mission_id: str, event_type: str, data: Dict[str, Any], user_id: str = "global"):
        """Publish mission events to Global Sovereign Telemetry."""
        from backend.broadcast_utils import SovereignBroadcaster
        
        # We map missions events to the global broadcast protocol
        SovereignBroadcaster.publish(event_type, {
            "mission_id": mission_id,
            "data": data,
            "timestamp": time.time()
        }, user_id=user_id)
        
        logger.debug(f"📡 [Global Broadcast] Mission {mission_id} -> {event_type}")

    def get_mission_state(self, mission_id: str) -> Optional[Dict[str, Any]]:


        """Retrieve state from Redis."""
        state_json = cache.get(f"mission:{mission_id}:state")
        if state_json:
            return json.loads(state_json)
        return None

distributed_orchestrator = DistributedOrchestrator()

class BrainOrchestrator:
    """
    Sovereign Orchestration Core v22.1.
    High-level API for the Cognitive Engine.
    """
    
    def __init__(self):
        self.planner = BrainPlanner()

    async def stream_request(self, user_id: str, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        [Brain-v22] Unified Thinking-Loop Stream.
        Yields tokens and activity events from the Cognitive Engine.
        """
        logger.info(f"🧠 [Orchestrator] Initiating Sovereign Stream for {user_id}")
        
        from .cognitive_engine import cognitive_engine
        
        last_state = None
        async for update in cognitive_engine.run(user_id, query):
            if update.get("event") == "final_state":
                last_state = update["data"]
            yield update
            
        if last_state:
            results = last_state.get("shared_context", {}).get("results", [])
            if results:
                final_text = results[-1].get("output", "")
                # Simulate streaming of the final result if it's too long
                for token in final_text.split(" "):
                    yield {"token": token + " "}
            
        yield {"event": "metadata", "data": {"status": "completed", "fidelity": last_state.get("shared_context", {}).get("score", 100) if last_state else 0}}

distributed_orchestrator = DistributedOrchestrator()
orchestrator = distributed_orchestrator


