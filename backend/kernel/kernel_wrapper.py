# backend/kernel/kernel_wrapper.py
import json
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class LeviKernel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LeviKernel, cls).__new__(cls)
            try:
                from .levi_kernel import LeviKernel as RustKernel
                cls._instance.rust_kernel = RustKernel()
                logger.info("🚀 [Kernel] Levi Rust Kernel initialized successfully.")
                # Start background telemetry poller
                import asyncio
                from backend.utils.runtime_tasks import create_tracked_task
                create_tracked_task(cls._instance._telemetry_poller(), name="kernel-telemetry-poller")
            except ImportError:
                logger.warning("⚠️ [Kernel] Levi Rust Kernel NOT FOUND. Falling back to Python (Simulated).")
                cls._instance.rust_kernel = None
        return cls._instance

    async def _telemetry_poller(self):
        """Polls the Rust kernel for telemetry pulses and broadcasts them."""
        from backend.broadcast_utils import SovereignBroadcaster
        while self.rust_kernel:
            try:
                # Poll the Rust side for any waiting pulses
                pulse = self.rust_kernel.get_telemetry()
                if pulse:
                    # Broadcast to the system:pulse channel for UI/SSE consumption
                    SovereignBroadcaster.publish(
                        "system:pulse",
                        {"type": "kernel_telemetry", "payload": json.loads(pulse)}
                    )
                else:
                    await asyncio.sleep(0.05) # 50ms poll interval
            except Exception as e:
                logger.error(f"[Kernel] Telemetry polling error: {e}")
                await asyncio.sleep(1)

    def classify_intent(self, user_input: str) -> Optional[str]:
        if not self.rust_kernel:
            return None
        try:
            return self.rust_kernel.classify_intent(user_input)
        except Exception as e:
            logger.error(f"[Kernel] Intent classification failed: {e}")
            return None

    def validate_dag(self, dag_id: str) -> bool:
        if not self.rust_kernel:
            return True # Assume valid in fallback
        try:
            return self.rust_kernel.validate_dag(dag_id)
        except Exception as e:
            logger.error(f"[Kernel] DAG validation failed: {e}")
            return False

    def sync_memory_batch(self, facts: List[Dict[str, Any]]):
        if not self.rust_kernel:
            return
        try:
            facts_json = json.dumps(facts)
            self.rust_kernel.sync_memory_batch(facts_json)
        except Exception as e:
            logger.error(f"[Kernel] Memory sync failed: {e}")

    def send_mission_request(self, mission_id: str, payload: str):
        if not self.rust_kernel:
            return
        try:
            # This would map to the Microkernel's message bus
            self.rust_kernel.send_message(json.dumps({
                "type": "MissionRequest",
                "mission_id": mission_id,
                "payload": payload
            }))
        except Exception as e:
            logger.error(f"[Kernel] Failed to send mission request: {e}")

    def restart_agent(self, agent_id: str):
        """Callback from Microkernel to restart a Python agent."""
        logger.warning(f"🔄 [Kernel] Restarting agent {agent_id}...")
        # Logic to restart the specific agent in the Orchestrator
        from backend.core.orchestrator import orchestrator
        if orchestrator:
            asyncio.create_task(orchestrator.reboot_engine(agent_id))

    def get_signing_key(self) -> bytes:
        """
        Sovereign v15.1: Non-Repudiation Key Retrieval.
        Retrieves the node's Ed25519 private key bytes for DCN pulse signing.
        """
        if self.rust_kernel and hasattr(self.rust_kernel, "get_signing_key"):
            return self.rust_kernel.get_signing_key()
        
        # Fallback: Deterministic derivation from DCN_SECRET (Sovereign mode)
        import hashlib
        import os
        secret = os.getenv("DCN_SECRET", "fallback_entropy_levi_ai_sovereign_32")
        return hashlib.sha256(secret.encode() + b"_signing_v1").digest()

    def spawn_task(self, name: str, command: str, args: List[str] = None) -> Optional[str]:
        """Sovereign v16.2: Native Process Spawning (Docker Replacement)."""
        if not self.rust_kernel:
            logger.warning("⚠️ [Kernel] Rust Kernel not found. Task spawning simulated.")
            return f"simulated-{name}"
        try:
            return self.rust_kernel.spawn_task(name, command, args or [])
        except Exception as e:
            logger.error(f"[Kernel] Failed to spawn task {name}: {e}")
            return None

    def kill_task(self, task_id: str):
        """Sovereign v16.2: Native Process Termination."""
        if self.rust_kernel:
            try:
                self.rust_kernel.kill_task(task_id)
            except Exception as e:
                logger.error(f"[Kernel] Failed to kill task {task_id}: {e}")

    def get_processes(self) -> List[Dict[str, Any]]:
        """Sovereign v16.2: Retrieve list of kernel-managed processes."""
        if not self.rust_kernel:
            return []
        try:
            return json.loads(self.rust_kernel.get_processes())
        except Exception as e:
            logger.error(f"[Kernel] Failed to get process list: {e}")
            return []

    def schedule_mission(self, mission_id: str, priority: str = "Normal"):
        """Sovereign v16.2: Kernel-level mission scheduling."""
        if self.rust_kernel:
            try:
                # priority: Critical, High, Normal, Low
                self.rust_kernel.schedule_mission(mission_id, json.dumps(priority))
            except Exception as e:
                logger.error(f"[Kernel] Failed to schedule mission {mission_id}: {e}")

    def update_mission_state(self, mission_id: str, state: str):
        """Sovereign v16.2: Update mission state in kernel registry."""
        if self.rust_kernel:
            try:
                # state: Queued, Analyzing, Executing, Verifying, Succeeded, Failed
                self.rust_kernel.update_mission_state(mission_id, json.dumps(state))
            except Exception as e:
                logger.error(f"[Kernel] Failed to update mission state {mission_id}: {e}")

    def get_gpu_metrics(self) -> Dict[str, Any]:
        """Sovereign v16.2: Retrieve GPU telemetry from kernel governance layer."""
        if not self.rust_kernel:
            return {"vram_total_mb": 0, "vram_used_mb": 0, "load_pct": 0, "temp_c": 0}
        try:
            return json.loads(self.rust_kernel.get_gpu_metrics())
        except Exception as e:
            logger.error(f"[Kernel] Failed to get GPU metrics: {e}")
            return {}

    def request_gpu_vram(self, agent_id: str, amount_mb: int) -> bool:
        """Sovereign v16.2: Request GPU VRAM allocation from kernel."""
        if not self.rust_kernel:
            return True
        try:
            return self.rust_kernel.request_gpu_vram(agent_id, amount_mb)
        except Exception as e:
            logger.error(f"[Kernel] GPU VRAM request failed for {agent_id}: {e}")
            return False

    def get_boot_report(self) -> Dict[str, Any]:
        """Sovereign v16.2: Retrieve kernel boot sequence report."""
        if not self.rust_kernel:
            return {}
        try:
            return json.loads(self.rust_kernel.get_boot_report())
        except Exception as e:
            logger.error(f"[Kernel] Failed to get boot report: {e}")
            return {}

    def get_fs_tree(self) -> Dict[str, Any]:
        """Sovereign v16.2: Retrieve virtual filesystem tree."""
        if not self.rust_kernel:
            return {}
        try:
            return json.loads(self.rust_kernel.get_fs_tree())
        except Exception as e:
            logger.error(f"[Kernel] Failed to get FS tree: {e}")
            return {}

    def get_drivers(self) -> List[Any]:
        """Sovereign v16.2: List active HAL drivers."""
        if not self.rust_kernel:
            return []
        try:
            return json.loads(self.rust_kernel.get_drivers())
        except Exception as e:
            logger.error(f"[Kernel] Failed to get drivers: {e}")
            return []

    def get_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """Sovereign v16.2: Retrieve capability set for a specific agent."""
        if not self.rust_kernel:
            return {"active": ["NetworkAccess", "FileSystemWrite"]}
        try:
            return json.loads(self.rust_kernel.get_agent_capabilities(agent_id))
        except Exception as e:
            logger.error(f"[Kernel] Failed to get capabilities for {agent_id}: {e}")
            return {}

    # --- Phase 4: Hardening & Optimization ---

    def allocate_vram(self, mission_id: str, amount_mb: int) -> bool:
        """Production-grade VRAM allocation with mission-id tracking."""
        if not self.rust_kernel:
            return True
        try:
            return self.rust_kernel.allocate_vram(mission_id, amount_mb)
        except Exception as e:
            logger.error(f"[Kernel] allocate_vram failed for {mission_id}: {e}")
            return False

    def spawn_isolated_task(self, task_id: str, cmd: str) -> Optional[int]:
        """Sovereign v16.2: Spawns an isolated process and returns its OS PID."""
        if not self.rust_kernel:
            logger.warning(f"⚠️ [Kernel] Simulated PID for {task_id}")
            return 9999
        try:
            return self.rust_kernel.spawn_isolated_task(task_id, cmd)
        except Exception as e:
            logger.error(f"[Kernel] spawn_isolated_task failed for {task_id}: {e}")
            return None

# Global singleton
kernel = LeviKernel()
