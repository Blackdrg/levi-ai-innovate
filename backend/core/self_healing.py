import logging
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from backend.core.orchestrator import _orchestrator as orchestrator
from backend.core.execution_state import CentralExecutionState, MissionState
from backend.broadcast_utils import SovereignBroadcaster
from backend.kernel.kernel_wrapper import kernel
from backend.redis_client import SovereignCache

logger = logging.getLogger(__name__)

class SelfHealingEngine:
    """
    Sovereign v17.0: Autonomous Self-Healing Engine.
    Monitors kernel health pulses and mission states to autonomously correct failures.
    """
    def __init__(self):
        self.is_running = False
        self._monitor_task = None
        self._pubsub_task = None
        self._retry_counts = {} # mission_id -> count

    async def start(self):
        if self.is_running: return
        self.is_running = True
        
        # 1. Start active resource monitor
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        # 2. Start passive pulse subscriber
        self._pubsub_task = asyncio.create_task(self._pulse_subscriber())
        
        logger.info("🩺 [SelfHealing] Engine STARTED. Monitoring system resilience.")

    async def _monitor_loop(self):
        """Active polling loop for state-machine consistency checks."""
        while self.is_running:
            try:
                await self._heal_resource_exhaustion()
            except Exception as e:
                logger.error(f"[SelfHealing] Monitor error: {e}")
            await asyncio.sleep(20)

    async def _pulse_subscriber(self):
        """Passive listener for system failure pulses."""
        client = SovereignCache.get_client()
        pubsub = client.pubsub()
        await asyncio.to_thread(pubsub.psubscribe, "sovereign:telemetry:*")
        
        while self.is_running:
            try:
                message = await asyncio.to_thread(pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    data = json.loads(message['data'])
                    await self._process_healing_pulse(data)
            except Exception as e:
                logger.error(f"[SelfHealing] Subscriber error: {e}")
                await asyncio.sleep(2)

    async def _process_healing_pulse(self, pulse: Dict[str, Any]):
        ptype = pulse.get("type")
        data = pulse.get("data", {})
        
        if ptype == "mission_error":
            mission_id = data.get("mission_id")
            if mission_id:
                asyncio.create_task(self._heal_failed_mission(mission_id, data.get("error")))
        
        elif ptype == "kernel_telemetry":
            await self.handle_kernel_pulse(data)

    async def _heal_failed_mission(self, mission_id: str, error_msg: str):
        """Analyzes mission failure and attempts autonomous recovery."""
        retries = self._retry_counts.get(mission_id, 0)
        if retries >= 2:
            logger.warning(f"🛑 [SelfHealing] Max retries reached for {mission_id}. Abandoning.")
            return

        self._retry_counts[mission_id] = retries + 1
        logger.info(f"🦾 [SelfHealing] MISSION FAILURE DETECTED: {mission_id}. Reason: {error_msg}")
        
        # Determine if we should retry with higher priority
        await self.trigger_autonomous_recovery(mission_id, "mission_failure_retry")

    async def _heal_resource_exhaustion(self):
        """Reacts to VRAM or Memory pressure reported by the HAL."""
        metrics = kernel.get_gpu_metrics()
        used = metrics.get("vram_used_mb", 0)
        total = metrics.get("vram_total_mb", 0)
        
        if total > 0 and (used / total) > 0.95:
            logger.warning(f"🚨 [SelfHealing] EMERGENCY VRAM EVICTION TRIGGERED ({used}/{total}MB).")
            # Signal the kernel to preempt low priority tasks
            processes = kernel.get_processes()
            for proc in processes:
                if proc.get("priority") == "Low":
                    logger.info(f"🧹 [SelfHealing] Preempting task {proc['id']} to recover VRAM.")
                    kernel.preempt_mission(proc["id"])
                    break

    async def handle_kernel_pulse(self, payload: Dict[str, Any]):
        """Reactive healing triggered by Kernel Telemetry pulses."""
        # Check for OOM signals or driver failures
        if payload.get("type") == "OOM-KILLED":
            mid = payload.get("mission_id")
            logger.critical(f"💣 [SelfHealing] KERNEL OOM-KILL DETECTED: {mid}. Initializing state recovery.")
            await self.trigger_autonomous_recovery(mid, "oom_recovery")

    async def trigger_autonomous_recovery(self, mission_id: str, reason: str):
        """Dispatches a 'Recovery Mission' to fix a perceived system failure."""
        logger.info(f"🦾 [SelfHealing] Launching Autonomous Recovery DAG for {mission_id}. Mode: {reason}")
        
        # Objective formatted for recursive decomposition (GoalEngine)
        objective = f"Recover from failure in {mission_id}. Reason: {reason}. Perform forensic sweep and resume with priority High."
        
        await orchestrator.handle_mission_request(
            request_id=f"heal_{mission_id}_{int(time.time())}",
            user_id="SYSTEM_HEALER",
            objective=objective,
            intent_type="recovery"
        )

self_healing = SelfHealingEngine()
