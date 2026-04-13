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

# Degradation Saturation Thresholds
THRESHOLD_L2_DOWNGRADE = 0.70 # 70% VRAM used
THRESHOLD_L1_DOWNGRADE = 0.85 # 85% VRAM used
THRESHOLD_MENTAL_COMPRESSION = 0.95 # 95% VRAM used

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
        """Probes hardware for NVIDIA GPUs using the centralized gpu_monitor."""
        from backend.utils.hardware import gpu_monitor
        
        try:
            if not gpu_monitor.has_gpu:
                raise Exception("No NVIDIA GPU detected by NVML.")
                
            info = gpu_monitor.get_vram_usage()
            if not info.get("active"):
                raise Exception("GPU Monitor query failed.")
                
            # NVML provides more precise data than nvidia-smi subprocess
            slots = [{
                "id": "gpu-0",
                "name": "NVIDIA Sovereign Accelerator",
                "vram_total_mb": int(info["total"] * 1024),
                "vram_free_mb": int(info["available"] * 1024),
                "utilization_percent": int(info.get("utilization", 0)),
                "is_simulated": False
            }]
            VRAMGuard.CPU_FALLBACK_ACTIVE = False
            return slots

        except Exception as e:
            logger.warning(f"[VRAMGuard] DEGRADED MODE (CPU Fallback): GPU probe failed ({e}).")
            VRAMGuard.CPU_FALLBACK_ACTIVE = True
            return self._get_heuristic_slots()
            
    async def enforce_capacity(self, model_tier: str):
        """
        Sovereign v15.0: Proactive Capacity Enforcement.
        Raises ResourceExhaustedError if the requested tier cannot be served locally.
        """
        if self.CPU_FALLBACK_ACTIVE:
            logger.info(f"[VRAMGuard] CPU Fallback active. Allowing {model_tier} in degraded mode.")
            return

        has_capacity = await self.check_capacity(model_tier)
        if not has_capacity:
            logger.critical(f"🚨 [VRAMGuard] Resource Exhaustion: Insufficient VRAM for tier {model_tier}")
            raise RuntimeError(f"Cognitive resource exhaustion: Local VRAM cannot accommodate {model_tier} model.")

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

    async def get_recommended_tier(self, requested_tier: str) -> str:
        """
        Sovereign v14.1.0: Advanced Multi-Tier Degradation.
        Determines the best model tier based on immediate VRAM pressure.
        """
        slots = await self.get_device_slots(force_refresh=True)
        if not slots: return "L1" # Safety fallback
        
        # We look at the most available slot
        best_slot = max(slots, key=lambda s: s["vram_free_mb"])
        usage_pct = 1.0 - (best_slot["vram_free_mb"] / best_slot["vram_total_mb"])
        
        if usage_pct > THRESHOLD_MENTAL_COMPRESSION: return "MENTAL_COMPRESSION"
        if usage_pct > THRESHOLD_L1_DOWNGRADE: return "L1"
        if usage_pct > THRESHOLD_L2_DOWNGRADE:
             # Downgrade L3 to L2 if pressure is high
             return "L2" if requested_tier == "L3" else requested_tier
             
        return requested_tier
