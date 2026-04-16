import asyncio
import logging
import uuid
import time
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
from backend.models.events import TaskManagerContract, SovereignEvent
from backend.utils.event_bus import sovereign_event_bus
from backend.utils.circuit_breaker import agent_breaker

logger = logging.getLogger(__name__)

class UnifiedTaskManager:
    """
    Sovereign v16.2: Unified Task Runtime.
    Central coordinator for all mission stages with resource governance and retry logic.
    """
    
    def __init__(self):
        self.active_tasks: Dict[str, TaskManagerContract] = {}
        # Hardware limits (governed by Rust Kernel or psutil)
        self.max_vram_usage = 0.85 # 85% threshold
        self.current_vram_load = 0.0

    async def register_task(self, module: str, action: str, payload: Dict[str, Any], mission_id: str = "system") -> str:
        """Enters a task into the unified queue and emits a QUEUED event."""
        task = TaskManagerContract(
            module=module,
            action=action,
            payload=payload
        )
        self.active_tasks[task.task_id] = task
        
        await sovereign_event_bus.emit("task_lifecycle", {
            "event_type": "TASK_QUEUED",
            "mission_id": mission_id,
            "payload": {
                "task_id": task.task_id,
                "module": module,
                "action": action
            },
            "source": f"task_manager:{module}"
        })
        
        logger.info(f"📋 [TaskManager] Task {task.task_id} registered for {module}:{action}")
        return task.task_id

    async def execute_task(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        Executes a task with circuit breakers, resource tracking, and retries.
        """
        task = self.active_tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in registry.")

        mission_id = kwargs.get("mission_id", "system")
        task.status = "PROCESSING"
        start_time = time.time()
        
        for attempt in range(1, task.retries + 1):
            try:
                # 1. Resource Governance Check (Hardened)
                await self._check_resource_limits()
                
                # 2. Circuit Breaker Wrapped Call
                result = await agent_breaker.call(func, *args, **kwargs)
                
                # 3. Success Update
                task.status = "COMPLETED"
                duration = time.time() - start_time
                
                await sovereign_event_bus.emit("task_lifecycle", {
                    "event_type": "TASK_COMPLETED",
                    "mission_id": mission_id,
                    "payload": {
                        "task_id": task_id,
                        "duration_ms": duration * 1000,
                        "module": task.module
                    },
                    "source": f"task_manager:{task.module}"
                })
                
                del self.active_tasks[task_id]
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ [TaskManager] Task {task_id} failed attempt {attempt}: {e}")
                if attempt == task.retries:
                    task.status = "FAILED"
                    await sovereign_event_bus.emit("task_lifecycle", {
                        "event_type": "TASK_FAILED",
                        "mission_id": mission_id,
                        "payload": {
                            "task_id": task_id,
                            "error": str(e),
                            "traceback": "..." # Simplified trace for payload
                        },
                        "source": f"task_manager:{task.module}"
                    })
                    raise e
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

    async def _check_resource_limits(self):
        """Hardware awareness loop. Blocks execution if VRAM/CPU exceeds safety threshold."""
        try:
            from backend.utils.hardware import gpu_monitor
            usage = gpu_monitor.get_vram_usage()
            if usage > self.max_vram_usage:
                logger.warning(f"🐢 [TaskManager] VRAM Limit reached ({usage*100:.1f}%). Throttling execution...")
                # Simple back-pressure: wait for vram to clear
                while gpu_monitor.get_vram_usage() > self.max_vram_usage:
                    await asyncio.sleep(1.0)
                logger.info("🟢 [TaskManager] VRAM within safety limits. Resuming execution.")
        except ImportError:
            # Fallback for systems without specific hardware monitoring
            pass

task_manager = UnifiedTaskManager()
