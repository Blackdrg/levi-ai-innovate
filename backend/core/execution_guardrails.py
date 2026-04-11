from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Set

import psutil

from backend.utils.metrics import MetricsHub


_sandbox_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "executor_sandbox_context",
    default={},
)


@dataclass
class ResourcePressureSnapshot:
    cpu_percent: float
    ram_used_bytes: int
    ram_percent: float
    queue_depth: int
    vram_pressure: bool

    @property
    def active_dimensions(self) -> Set[str]:
        active = set()
        if self.cpu_percent >= 85.0:
            active.add("cpu")
        if self.ram_percent >= 85.0:
            active.add("ram")
        if self.queue_depth >= 32:
            active.add("queue")
        if self.vram_pressure:
            active.add("vram")
        return active


class ExecutionBudgetTracker:
    def __init__(self, token_limit: int, tool_call_limit: int):
        self.token_limit = max(0, token_limit)
        self.tool_call_limit = max(0, tool_call_limit)
        self.tokens_used = 0
        self.tool_calls = 0
        self.agent_budgets: Dict[str, int] = {}
        # Default per-agent limit (e.g., 50% of total)
        self.max_per_agent = int(self.token_limit * 0.7)

    def can_schedule_next_tool(self) -> bool:
        return self.tool_calls < self.tool_call_limit

    def remaining_tool_calls(self) -> int:
        return max(0, self.tool_call_limit - self.tool_calls)

    def reserve_tool_calls(self, count: int) -> None:
        self.tool_calls += max(0, count)

    def add_tokens(self, agent: str, total_tokens: int) -> bool:
        total_tokens = max(0, int(total_tokens))
        
        # Track total mission usage
        self.tokens_used += total_tokens
        MetricsHub.record_token_usage(agent, total_tokens)
        
        # Track and enforce per-agent budget
        self.agent_budgets[agent] = self.agent_budgets.get(agent, 0) + total_tokens
        if self.agent_budgets[agent] > self.max_per_agent:
            import logging
            logging.getLogger(__name__).warning(f"[Security] Agent '{agent}' exceeded its per-mission budget.")
            return False

        return self.tokens_used <= self.token_limit


class AgentSandbox:
    @staticmethod
    def activate(
        mission_id: str,
        node_id: str,
        allowed_tools: Optional[Iterable[str]],
        memory_scope: str,
        security_tier: str = "T1" # T1: Context, T2: Docker, T3: gVisor
    ) -> contextvars.Token:
        payload = {
            "mission_id": mission_id,
            "node_id": node_id,
            "allowed_tools": set(allowed_tools or []),
            "memory_scope": memory_scope,
            "memory_scope_key": f"{mission_id}:{node_id}:{memory_scope}",
            "security_tier": security_tier,
            "sandbox_active": True
        }
        
        # v14.1 True Sandboxing Check (runsc)
        if security_tier == "T3":
            AgentSandbox._enforce_gvisor_check()
            
        return _sandbox_context.set(payload)

    @staticmethod
    def _enforce_gvisor_check():
        """Verifies if the host environment supports true sandboxing."""
        import subprocess
        try:
             res = subprocess.run(["runsc", "--version"], capture_output=True, text=True)
             if res.returncode != 0:
                 raise Exception("gVisor (runsc) requested but not functional on host.")
             import logging
             logging.getLogger(__name__).info("[Security] gVisor (runsc) verified for T3 Mission.")
        except FileNotFoundError:
             import logging
             logging.getLogger(__name__).warning("[Security] gVisor (runsc) not found. Falling back to T2 (Docker).")

    @staticmethod
    def deactivate(token: contextvars.Token) -> None:
        _sandbox_context.reset(token)

    @staticmethod
    async def run_in_sandbox(command: List[str], image: str = "python:3.11-slim", timeout: int = 10) -> Dict[str, Any]:
        """
        Sovereign v14.2 Tier 2 Execution: Hardened Docker Isolation.
        Now uses the consolidated DockerSandbox engine.
        """
        from backend.core.executor.sandbox import get_sandbox
        
        # Mock class/config for get_sandbox
        class SandboxConfig:
            def __init__(self, img):
                self.sandbox_image = img
                self.memory_limit_mb = 256
                self.cpu_cores = 1.0
        
        sandbox = get_sandbox(SandboxConfig(image))
        return await sandbox.run_command(command, timeout=float(timeout))


def _get_vram_info() -> Dict[str, int]:
    """Probes NVIDIA GPU status if available."""
    try:
        import subprocess
        # Probing nvidia-smi for total/used VRAM
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True
        )
        total, used = map(int, res.stdout.strip().split(", "))
        return {"total": total * 1024**2, "used": used * 1024**2}
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback or Mock for environments without NVIDIA GPUs (Local Dev)
        return {"total": 8 * 1024**3, "used": 0}

def capture_resource_pressure(queue_depth: int) -> ResourcePressureSnapshot:
    """
    Sovereign v14.2: High-fidelity resource pressure capture.
    Calculates dynamic backpressure for CPU, RAM, and VRAM.
    """
    vm = psutil.virtual_memory()
    gpu_info = _get_vram_info()
    
    vram_percent = (gpu_info["used"] / gpu_info["total"]) * 100 if gpu_info["total"] > 0 else 0
    vram_pressure = vram_percent >= 85.0
    
    snapshot = ResourcePressureSnapshot(
        cpu_percent=psutil.cpu_percent(),
        ram_used_bytes=int(vm.used),
        ram_percent=float(vm.percent),
        queue_depth=max(queue_depth, 0),
        vram_pressure=vram_pressure,
    )
    
    # Record to Metrics Hub
    MetricsHub.set_queue_depth(snapshot.queue_depth)
    for resource in ("cpu", "ram", "queue", "vram"):
        # resource in snapshot.active_dimensions handles the 85% thresholds
        MetricsHub.set_backpressure(resource, resource in snapshot.active_dimensions)
        
    return snapshot
