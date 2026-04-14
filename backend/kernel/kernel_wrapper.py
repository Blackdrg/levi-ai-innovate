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

# Global singleton
kernel = LeviKernel()
