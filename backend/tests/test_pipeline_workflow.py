import sys
import types

import pytest


def test_policy_bridge_preserves_agent_and_budget_contracts():
    sys.modules.setdefault(
        "backend.core.engine",
        types.SimpleNamespace(run_orchestrator=None, LeviOrchestrator=None),
    )
    from backend.services.brain_service import BrainPolicy
    from backend.core.workflow_contract import bridge_policy

    policy = BrainPolicy(
        mode="RESEARCH",
        enable={
            "planner": True,
            "critic": True,
            "retrieval": True,
            "browser": True,
            "docker": False,
            "sandbox": True,
        },
        execution={
            "parallel_waves": 3,
            "max_retries": 2,
            "retry_strategy": "exp_backoff_jitter",
            "budget": {
                "cpu_time_limit_ms": 1234,
                "token_limit": 4321,
                "tool_call_limit": 7,
                "max_dag_depth": 5,
                "recompute_cycles": 2,
                "max_cpu_percent": 80,
                "max_ram_percent": 81,
                "queue_depth_limit": 9,
            },
        },
        llm={"local_only": True, "fallback_allowed": False},
        memory={"redis": True, "postgres": True, "neo4j": True, "faiss": True},
    )

    decision = bridge_policy(policy)

    assert decision.enable_agents["retrieval"] is True
    assert decision.enable_agents["browser"] is True
    assert decision.execution_policy.sandbox_required is True
    assert decision.execution_policy.budget.token_limit == 4321
    assert decision.execution_policy.budget.queue_depth_limit == 9
    assert decision.memory_policy.faiss is True


def test_workflow_contract_reports_designated_stages():
    from backend.core.orchestrator_types import ToolResult
    from backend.services.brain_service import BrainPolicy
    from backend.core.task_graph import TaskGraph, TaskNode
    from backend.core.workflow_contract import bridge_policy, validate_workflow_integrity

    task_graph = TaskGraph(
        nodes=[
            TaskNode(
                id="t_core",
                agent="chat_agent",
                description="core",
                inputs={"input": "hello"},
            )
        ]
    )
    decision = bridge_policy(
        BrainPolicy(
            mode="BALANCED",
            enable={"planner": True, "critic": False, "retrieval": False, "browser": False, "docker": False, "sandbox": False},
            execution={"parallel_waves": 1, "max_retries": 1, "retry_strategy": "exp_backoff_jitter", "budget": {"tool_call_limit": 5}},
            llm={"local_only": True, "fallback_allowed": False},
            memory={"redis": True, "postgres": True, "neo4j": False, "faiss": True},
        )
    )

    workflow = validate_workflow_integrity(
        "req-1",
        perception={"intent": types.SimpleNamespace(intent_type="chat")},
        goal=types.SimpleNamespace(objective="answer user"),
        task_graph=task_graph,
        results=[ToolResult(success=True, message="hello back", agent="chat_agent", data={}, total_tokens=10)],
        memory_event={"id": "mem1", "checksum": "abc", "version": 1},
    )

    assert decision.execution_policy.budget.tool_call_limit == 5
    assert workflow["healthy"] is True
    assert workflow["node_count"] == 1
    assert workflow["result_count"] == 1
    assert workflow["stages"][0] == "gateway"
    assert "executor" in workflow["stages"]


def test_planner_compatibility_helpers_are_available():
    from backend.core.planner import call_lightweight_llm, detect_sensitivity

    assert callable(call_lightweight_llm)
    assert detect_sensitivity("my password is secret") is True
    assert detect_sensitivity("hello world") is False
