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

    def can_schedule_next_tool(self) -> bool:
        return self.tool_calls < self.tool_call_limit

    def remaining_tool_calls(self) -> int:
        return max(0, self.tool_call_limit - self.tool_calls)

    def reserve_tool_calls(self, count: int) -> None:
        self.tool_calls += max(0, count)

    def add_tokens(self, agent: str, total_tokens: int) -> bool:
        total_tokens = max(0, int(total_tokens))
        self.tokens_used += total_tokens
        MetricsHub.record_token_usage(agent, total_tokens)
        return self.tokens_used <= self.token_limit


class AgentSandbox:
    @staticmethod
    def activate(
        mission_id: str,
        node_id: str,
        allowed_tools: Optional[Iterable[str]],
        memory_scope: str,
    ) -> contextvars.Token:
        payload = {
            "mission_id": mission_id,
            "node_id": node_id,
            "allowed_tools": set(allowed_tools or []),
            "memory_scope": memory_scope,
            "memory_scope_key": f"{mission_id}:{node_id}:{memory_scope}",
        }
        return _sandbox_context.set(payload)

    @staticmethod
    def deactivate(token: contextvars.Token) -> None:
        _sandbox_context.reset(token)

    @staticmethod
    def current() -> Dict[str, Any]:
        return dict(_sandbox_context.get({}))

    @staticmethod
    def tool_allowed(tool_name: str) -> bool:
        ctx = _sandbox_context.get({})
        allowed = ctx.get("allowed_tools") or set()
        return not allowed or tool_name in allowed


def capture_resource_pressure(vram_pressure: bool, queue_depth: int) -> ResourcePressureSnapshot:
    vm = psutil.virtual_memory()
    snapshot = ResourcePressureSnapshot(
        cpu_percent=psutil.cpu_percent(),
        ram_used_bytes=int(vm.used),
        ram_percent=float(vm.percent),
        queue_depth=max(queue_depth, 0),
        vram_pressure=bool(vram_pressure),
    )
    MetricsHub.set_queue_depth(snapshot.queue_depth)
    for resource in ("cpu", "ram", "queue", "vram"):
        MetricsHub.set_backpressure(resource, resource in snapshot.active_dimensions)
    return snapshot
