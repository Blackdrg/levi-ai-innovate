import importlib
import importlib.util
import pathlib
import sys
import types

import pytest


def _stub_core_engine():
    sys.modules.setdefault(
        "backend.core.engine",
        types.SimpleNamespace(run_orchestrator=None, LeviOrchestrator=None),
    )


def _load_guardrails_module():
    module_name = "phase4_guardrails_test"
    module_path = pathlib.Path("backend/core/execution_guardrails.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_task_graph_rejects_orphan_nodes():
    _stub_core_engine()
    task_graph_mod = importlib.import_module("backend.core.task_graph")

    graph = task_graph_mod.TaskGraph(
        nodes=[
            task_graph_mod.TaskNode(id="a", agent="chat_agent", description="a", inputs={"input": "a"}),
            task_graph_mod.TaskNode(id="b", agent="chat_agent", description="b", inputs={"input": "b"}),
        ]
    )

    with pytest.raises(ValueError, match="Orphan nodes"):
        graph.validate_dag()


def test_task_graph_rejects_disconnected_components():
    _stub_core_engine()
    task_graph_mod = importlib.import_module("backend.core.task_graph")

    graph = task_graph_mod.TaskGraph(
        nodes=[
            task_graph_mod.TaskNode(id="a", agent="chat_agent", description="a", inputs={"input": "a"}),
            task_graph_mod.TaskNode(id="b", agent="chat_agent", description="b", inputs={"input": "b"}, dependencies=["a"]),
            task_graph_mod.TaskNode(id="c", agent="chat_agent", description="c", inputs={"input": "c"}),
            task_graph_mod.TaskNode(id="d", agent="chat_agent", description="d", inputs={"input": "d"}, dependencies=["c"]),
        ]
    )

    with pytest.raises(ValueError, match="Disconnected"):
        graph.validate_dag()


def test_memory_consistency_detects_version_conflict(monkeypatch):
    fake = types.SimpleNamespace(store={})

    def get(key):
        return fake.store.get(key)

    def setex(key, ttl, value):
        fake.store[key] = value
        return True

    def rpush(key, value):
        fake.store.setdefault(key, [])
        fake.store[key].append(value)
        return len(fake.store[key])

    redis_mod = types.SimpleNamespace(r=fake, HAS_REDIS=True)
    fake.get = get
    fake.setex = setex
    fake.rpush = rpush
    sys.modules["backend.db.redis"] = redis_mod

    consistency = importlib.reload(importlib.import_module("backend.memory.consistency"))
    consistency.MemoryConsistencyManager.register_event("u1", {"id": "item-1", "type": "fact"})

    with pytest.raises(ValueError, match="Version conflict"):
        consistency.MemoryConsistencyManager.register_event(
            "u1",
            {"id": "item-1", "type": "fact", "expected_version": 999},
        )


def test_budget_tracker_enforces_token_and_tool_limits():
    _stub_core_engine()
    guardrails = _load_guardrails_module()

    tracker = guardrails.ExecutionBudgetTracker(token_limit=10, tool_call_limit=2)
    assert tracker.can_schedule_next_tool() is True

    tracker.reserve_tool_calls(1)
    assert tracker.remaining_tool_calls() == 1
    assert tracker.add_tokens("chat_agent", 4) is True
    assert tracker.add_tokens("chat_agent", 7) is False


def test_agent_sandbox_blocks_out_of_contract_tools():
    _stub_core_engine()
    guardrails = _load_guardrails_module()

    token = guardrails.AgentSandbox.activate(
        mission_id="m1",
        node_id="n1",
        allowed_tools=["chat_agent"],
        memory_scope="task",
    )
    try:
        assert guardrails.AgentSandbox.tool_allowed("chat_agent") is True
        assert guardrails.AgentSandbox.tool_allowed("search_agent") is False
        context = guardrails.AgentSandbox.current()
        assert context["memory_scope_key"] == "m1:n1:task"
    finally:
        guardrails.AgentSandbox.deactivate(token)


def test_resource_pressure_detects_queue_backpressure():
    _stub_core_engine()
    guardrails = _load_guardrails_module()

    snapshot = guardrails.capture_resource_pressure(vram_pressure=False, queue_depth=64)
    assert "queue" in snapshot.active_dimensions
