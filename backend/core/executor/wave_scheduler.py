"""
LEVI-AI Wave Scheduler v15.0.0-GA.
Handles parallel dispatch of task waves with resource-aware admission control.
"""

import asyncio
import logging
from typing import List, Dict, Any, Set, Optional, Callable

from ..orchestrator_types import ToolResult
from ..execution_guardrails import capture_resource_pressure
from backend.utils.logger import get_logger

logger = get_logger("wave_scheduler")

class WaveScheduler:
    """
    Sovereign Wave Scheduler.
    Partitioning and executing TaskGraph in concurrent waves.
    """
    
    def __init__(self, max_concurrent_waves: int = 8, max_nodes_per_mission: int = 25):
        self.max_concurrent_waves = max_concurrent_waves
        self.max_nodes_per_mission = max_nodes_per_mission
        self._shutdown_event = asyncio.Event()

    async def execute_waves(self, graph: Any, execute_node_fn: Callable, mission_context: Dict[str, Any]) -> List[ToolResult]:
        """
        Executes a TaskGraph in topological waves with parallel dispatch and admission control.
        """
        mission_id = mission_context.get("mission_id", "global")
        results: Dict[str, ToolResult] = {}
        completed_ids: Set[str] = set()
        
        # 1. Kernel-Driven DAG Validation & Pre-Computation (v15.1)
        from backend.kernel.kernel_wrapper import kernel
        if not kernel.validate_dag(mission_id):
            logger.error(f"❌ [WaveScheduler] DAG Cycle Detected or Validation Failed (Kernel) for {mission_id}")
            return []
            
        # 2. Get Waves (Prefer Kernel-Ordered Waves)
        if not hasattr(graph, "get_execution_waves"):
            logger.error(f"❌ [WaveScheduler] Graph object missing 'get_execution_waves' method.")
            return []
            
        waves = graph.get_execution_waves()
        logger.info(f"🌊 [WaveScheduler] Mission {mission_id}: {len(waves)} waves identified (Validated by Kernel).")

        total_nodes_executed = 0

        for wave_idx, wave_nodes in enumerate(waves):
            if wave_idx >= self.max_concurrent_waves:
                logger.warning(f"⚠️ [WaveScheduler] Max waves ({self.max_concurrent_waves}) reached. Truncating.")
                break

            # Mission Cancellation Check
            from backend.utils.mission import MissionControl
            if MissionControl.is_cancelled(mission_id) or self._shutdown_event.is_set():
                logger.warning(f"🛑 [WaveScheduler] Mission {mission_id} aborted before wave {wave_idx}.")
                break

            logger.info(f"🚀 [WaveScheduler] Wave {wave_idx} | Dispatching {len(wave_nodes)} nodes...")

            # --- Resource-Aware Admission Control ---
            pressure = capture_resource_pressure(queue_depth=len(wave_nodes))
            vram_active = pressure.vram_pressure
            cpu_p = pressure.cpu_percent / 100.0
            ram_p = pressure.ram_percent / 100.0

            # Parallel tasks in this wave
            wave_tasks = []
            
            # If pressure is high, we limit concurrency within the wave
            concurrency_limit = len(wave_nodes)
            if vram_active or cpu_p > 0.9 or ram_p > 0.9:
                logger.warning(f"⚠️ [WaveScheduler] CRITICAL Resource Pressure ({cpu_p:.2f} CPU). Throttling wave {wave_idx} to serial.")
                concurrency_limit = 1
            elif cpu_p > 0.75:
                logger.info(f"⏳ [WaveScheduler] High Resource Pressure. Limiting wave concurrency.")
                concurrency_limit = min(2, len(wave_nodes))

            async def wrapped_execute(node):
                try:
                    return await execute_node_fn(node, results, wave_idx)
                except Exception as e:
                    logger.error(f"💀 [WaveScheduler] Node {node.id} crashed: {e}")
                    return ToolResult(success=False, error=str(e), agent=getattr(node, "agent", "unknown"))

            # Execute wave nodes with concurrency limit
            semaphore = asyncio.Semaphore(concurrency_limit)
            
            async def sem_execute(node):
                async with semaphore:
                    return await wrapped_execute(node)

            batch_tasks = [asyncio.create_task(sem_execute(node)) for node in wave_nodes if node.id not in completed_ids]
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks)
                for node, res in zip(wave_nodes, batch_results):
                    results[node.id] = res
                    completed_ids.add(node.id)
                    total_nodes_executed += 1
                    
                    # Graph result update for next wave
                    if hasattr(graph, "mark_complete"):
                        graph.mark_complete(node.id, res)
                    
                    # Stop if critical node fails
                    if not res.success and getattr(node, "critical", False):
                        logger.error(f"💥 [WaveScheduler] Critical node {node.id} failed. Terminating DAG.")
                        return list(results.values())

            if total_nodes_executed >= self.max_nodes_per_mission:
                logger.warning(f"🛑 [WaveScheduler] Max nodes ({self.max_nodes_per_mission}) reached.")
                break

        return list(results.values())

    def stop(self):
        self._shutdown_event.set()
