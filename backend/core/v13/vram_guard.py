"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
VRAM Guard: Hardware-aware cognitive backpressure and resource safety.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

VRAM_SAFETY_BUFFER_PERCENT = float(os.getenv("VRAM_SAFETY_BUFFER_PERCENT", "0.15")) # Buffer for VRAM backpressure 
MIN_FREE_GB = 1.0 # Absolute minimum 1GB free

class VRAMPool:
    """
    Sovereign VRAM Resource Pool v14.0.0.
    Manages available VRAM in MB across all device slots.
    """
    def __init__(self, total_mb: int):
        self.total_mb = total_mb
        self.available_mb = total_mb
        self.condition = asyncio.Condition()

    async def acquire(self, amount_mb: int, burst_mode: bool = False) -> bool:
        """
        Sovereign v14.0: Hybrid VRAM Acquisition.
        Returns True if acquired locally, False if Burst (Cloud) transition is required.
        """
        async with self.condition:
            if self.available_mb >= amount_mb:
                self.available_mb -= amount_mb
                logger.info(f"[VRAMPool] Acquired {amount_mb}MB locally (Remaining: {self.available_mb}MB)")
                return True
            
            # If local VRAM is full
            if burst_mode:
                logger.warning(f"[VRAMPool] Local Saturation. Transitioning to CLOUD BURST for {amount_mb}MB request.")
                return False # Signal Burst Mode
                
            # Legacy/Strict Mode: Wait for local resources
            while self.available_mb < amount_mb:
                logger.debug(f"[VRAMPool] Waiting for {amount_mb}MB (Available: {self.available_mb}MB)")
                try:
                    await asyncio.wait_for(self.condition.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    if burst_mode: return False
                    raise Exception(f"VRAM Deadlock: Resource timeout after 10s for {amount_mb}MB")
            
            self.available_mb -= amount_mb
            return True

    async def release(self, amount_mb: int):
        """Releases VRAM back to the pool and notifies waiters."""
        async with self.condition:
            self.available_mb = min(self.total_mb, self.available_mb + amount_mb)
            logger.info(f"[VRAMPool] Released {amount_mb}MB (New Available: {self.available_mb}MB)")
            self.condition.notify_all()

    @property
    def value(self) -> int:
        return self.available_mb

class VRAMGuard:
    """
    Sovereign VRAM Guard v14.0.0.
    Handles real-time hardware telemetry and heuristic-based resource gating.
    Supports Multi-GPU pooling by treating each GPU as a 'DeviceSlot'.
    """

    CPU_FALLBACK_ACTIVE = False

    def __init__(self):
        self.device_slots = []
        self._refresh_lock = asyncio.Lock()

    async def get_device_slots(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Returns a list of available GPU device slots and their current VRAM."""
        async with self._refresh_lock:
            if not self.device_slots or force_refresh:
                self.device_slots = await self._probe_hardware()
            return self.device_slots

    async def _probe_hardware(self) -> List[Dict[str, Any]]:
        """Probes hardware for NVIDIA GPUs using nvidia-smi."""
        try:
            # Audit Point 52: Hardware Telemetry via subprocess
            # We use a non-blocking approach to run nvidia-smi
            process = await asyncio.create_subprocess_exec(
                "nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,utilization.gpu", "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"nvidia-smi failed: {stderr.decode()}")

            slots = []
            for line in stdout.decode().strip().split("\n"):
                if not line: continue
                idx, name, total, free, util = [x.strip() for x in line.split(",")]
                slots.append({
                    "id": f"gpu-{idx}",
                    "name": name,
                    "vram_total_mb": int(total),
                    "vram_free_mb": int(free),
                    "utilization_percent": int(util),
                    "is_simulated": False
                })
            VRAMGuard.CPU_FALLBACK_ACTIVE = False
            return slots

        except Exception as e:
            logger.warning(f"[VRAMGuard] DEGRADED MODE (CPU Fallback): NVIDIA-SMI probe failed ({e}).")
            VRAMGuard.CPU_FALLBACK_ACTIVE = True
            return self._get_heuristic_slots()

    def _get_heuristic_slots(self) -> List[Dict[str, Any]]:
        """Fallback for local dev or systems without NVML/nvidia-smi."""
        # Retrieve from environment or default to 8GB 'Generic Slot'
        total_vram = int(os.getenv("HEURISTIC_VRAM_MB", "8192"))
        return [{
            "id": "gpu-0",
            "name": "Heuristic Sovereign Accelerator",
            "vram_total_mb": total_vram,
            "vram_free_mb": total_vram, # Assume free in simulation
            "utilization_percent": 0,
            "is_simulated": True
        }]

    @staticmethod
    def get_vram_requirement(model_tier: str) -> int:
        """
        Returns estimated VRAM requirement in MB for a given model tier.
        Reflects actual Llama 3.3 70B and Phi-3 footprints.
        """
        tier_map = {
            "L1": 4096,   # 4GB (Phi-3-Mini)
            "L2": 12288,  # 12GB (Llama 3.1 8B 128k Context)
            "L3": 49152,  # 48GB (Llama 3.3 70B Q4_K_M)
            "L4": 81920   # 80GB (A100/H100 Max Utility)
        }
        return tier_map.get(model_tier, 8192) # Default to 8GB for safety

    async def check_capacity(self, model_tier: str) -> bool:
        """Checks if any device slot can accommodate the requested model tier."""
        req_mb = self.get_vram_requirement(model_tier)
        slots = await self.get_device_slots(force_refresh=True)
        
        for s in slots:
            # Check if (Free VRAM - Safety Buffer) >= Required MB
            usable_free_mb = s["vram_free_mb"] - (s["vram_total_mb"] * VRAM_SAFETY_BUFFER_PERCENT)
            if usable_free_mb >= req_mb:
                return True
        
        return False
