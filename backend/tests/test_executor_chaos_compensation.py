from __future__ import annotations

import pytest

from backend.core.executor import GraphExecutor
from backend.core.execution_state import CentralExecutionState
from backend.core.orchestrator_types import FailurePolicy, TaskExecutionContract
from backend.core.task_graph import TaskNode


class _FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value
        return True


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_mode", ["timeout", "malformed"])
async def test_executor_executes_compensation_on_terminal_failure(monkeypatch, failure_mode):
    monkeypatch.setattr("backend.core.execution_state.HAS_REDIS", True)
    monkeypatch.setattr("backend.core.execution_state.redis_client", _FakeRedis())
    executor = GraphExecutor()
    mission_sm = CentralExecutionState("mission-chaos", trace_id="mission-chaos", user_id="user-1")
    mission_sm.initialize()

    node = TaskNode(
        id="n1",
        agent="chat_agent",
        description="test node",
        inputs={},
        compensation_action="log_failure:n1",
        contract=TaskExecutionContract(
            task_id="n1",
            input_schema={"input": {"type": "str", "required": True}},
            output_schema={"success": {"type": "bool", "required": True}},
            max_retries=0,
            failure_policy=FailurePolicy(on_failure="compensate", compensate=True),
        ),
    )
    perception = {"request_id": "mission-chaos", "input": "hello", "context": {}}

    async def fake_call_tool(*args, **kwargs):
        if failure_mode == "timeout":
            raise TimeoutError("forced timeout")
        return {"unexpected": "shape"}

    monkeypatch.setattr("backend.core.executor.call_tool", fake_call_tool)

    result = await executor._execute_node(node, {}, perception, mission_sm=mission_sm)
    state = mission_sm._load()
    events = state["nodes"]["n1"]["events"]

    assert result.success is False
    assert result.data["compensation"]["status"] == "executed"
    assert any(event["status"] == "compensated" for event in events)


@pytest.mark.asyncio
async def test_executor_logs_structured_node_fields(monkeypatch, caplog):
    executor = GraphExecutor()
    node = TaskNode(id="n2", agent="chat_agent", description="structured log", inputs={})
    perception = {"request_id": "mission-log", "input": "hello", "context": {}}

    async def fake_call_tool(*args, **kwargs):
        return {"success": True, "message": "ok", "agent": "chat_agent"}

    monkeypatch.setattr("backend.core.executor.call_tool", fake_call_tool)

    with caplog.at_level("INFO"):
        result = await executor._execute_node(node, {}, perception)

    assert result.success is True
    assert any(getattr(record, "mission_id", None) == "mission-log" for record in caplog.records)
    assert any(getattr(record, "node_id", None) == "n2" for record in caplog.records)
