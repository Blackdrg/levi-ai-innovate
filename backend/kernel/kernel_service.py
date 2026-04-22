# backend/kernel/kernel_service.py
"""
Sovereign Kernel Service API Layer (v22.1).
Replaces raw syscall abstractions with a high-level, production-grade API.
Acts as the bridge between Python-layer cognition and Rust-layer hardware governance.
"""
import logging
import json
from typing import List, Optional, Dict, Any
from .kernel_wrapper import kernel

logger = logging.getLogger(__name__)

class SovereignKernelService:
    """
    Real API layer for the Sovereign OS.
    Standardizes interaction with HAL-0 (Rust) and hardware substrate.
    """
    
    def __init__(self):
        self.kernel = kernel

    # ── Memory & Resource Governance ──────────────────────────────────────────

    async def reserve_memory(self, size_kb: int, vram_id: int = 0) -> bool:
        """Reserve virtual memory or VRAM segments for agent waves."""
        try:
            logger.debug(f" [KernelAPI] Reserving {size_kb}KB on VRAM_{vram_id}")
            return self.kernel.allocate_vram("global", size_kb // 1024)
        except Exception as e:
            logger.error(f"🚨 [KernelAPI] Memory reservation failed: {e}")
            return False

    async def get_resource_usage(self) -> Dict[str, Any]:
        """Fetch real-time GPU/CPU metrics from HAL-0."""
        try:
            return self.kernel.get_gpu_metrics()
        except Exception:
            return {"status": "error", "vram_used_mb": 0}

    async def flush_resource_buffers(self):
        """Flush hardware-bound memory buffers (VRAM, Cache)."""
        logger.warning("🧹 [KernelAPI] Flushing resource buffers...")
        try:
            self.kernel.flush_vram_buffer()
        except Exception as e:
            logger.error(f" [KernelAPI] Buffer flush failed: {e}")

    # ── Mission Lifecycle & Telemetry ─────────────────────────────────────────

    async def schedule_mission(self, mission_id: str, priority: str = "Normal"):
        """Register a mission with the kernel scheduler."""
        try:
            self.kernel.schedule_mission(mission_id, priority)
        except Exception as e:
            logger.error(f" [KernelAPI] Mission scheduling failed: {e}")

    async def update_mission_state(self, mission_id: str, state: str):
        """Update the kernel-level mission state tracker."""
        try:
            self.kernel.update_mission_state(mission_id, state)
        except Exception as e:
            logger.debug(f" [KernelAPI] State update ignored: {e}")

    async def write_telemetry_record(self, event_id: int, arg1: int = 0, arg2: int = 0):
        """Write a forensic telemetry record to the hardware-bound KHTP bridge."""
        try:
            self.kernel.write_record(event_id, arg1, arg2)
        except Exception as e:
            logger.error(f" [KernelAPI] Telemetry write failed: {e}")

    # ── Process & Task Execution ──────────────────────────────────────────────

    async def spawn_agent_wave(self, agent_id: str, command: str, args: List[str] = None) -> Optional[str]:
        """Spawn a sandboxed agent process (Ring-3)."""
        try:
            logger.info(f"🚀 [KernelAPI] Spawning wave for agent: {agent_id}")
            return self.kernel.spawn_task(agent_id, command, args)
        except Exception as e:
            logger.error(f" [KernelAPI] Wave spawn failed: {e}")
            return None

    async def kill_agent_wave(self, wave_id: str):
        """Terminate an active agent wave."""
        self.kernel.kill_task(wave_id)

    # ── Security & Forensic Finality ──────────────────────────────────────────

    async def sign_mission_proof(self, mission_id: str, payload_hash: str) -> str:
        """Request hardware-bound BFT signature (0x03) for mission truth."""
        logger.debug(f"🔐 [KernelAPI] Signing mission proof: {mission_id}")
        return self.kernel.emit_heartbeat(0, json.dumps({"mid": mission_id, "hash": payload_hash}))

    async def verify_proof(self, proof_json: str, public_key: str) -> bool:
        """Verify a BFT proof via the native Rust executor."""
        return self.kernel.verify_heartbeat(proof_json, public_key)

    # ── Memory Resonance (MCM) Bridge ─────────────────────────────────────────

    async def graduate_fact_to_substrate(self, fact_id: str, tier: int = 3) -> bool:
        """Promote a fact to hardware-bound persistence (MCM T3)."""
        logger.info(f"🎓 [KernelAPI] Graduating fact {fact_id} to Tier {tier}")
        # Replaces raw syscall(0x06)
        return self.kernel.sys_call("mcm", json.dumps({"MCM_GRADUATE": {"fid": fact_id, "tier": tier}})) == "OK"

    # ── Hardware / Drivers ────────────────────────────────────────────────────

    async def get_hal_report(self) -> Dict[str, Any]:
        """Get the full boot and driver report from the kernel."""
        return {
            "boot": self.kernel.get_boot_report(),
            "drivers": self.kernel.get_drivers(),
            "rings": [0, 1, 3]
        }

# Global singleton
kernel_service = SovereignKernelService()
