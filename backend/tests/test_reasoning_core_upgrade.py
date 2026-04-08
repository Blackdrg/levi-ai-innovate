import importlib
import sys
import types

import pytest


def _stub_core_engine():
    sys.modules.setdefault(
        "backend.core.engine",
        types.SimpleNamespace(run_orchestrator=None, LeviOrchestrator=None),
    )


@pytest.mark.asyncio
async def test_reasoning_core_produces_confidence_and_safe_mode():
    _stub_core_engine()
    reasoning_core = importlib.import_module("backend.core.reasoning_core")
    task_graph_mod = importlib.import_module("backend.core.task_graph")

    graph = task_graph_mod.TaskGraph()
    graph.add_node(
        task_graph_mod.TaskNode(
            id="t1",
            agent="chat_agent",
            description="primary",
            inputs={"input": "test"},
        )
    )
    graph.add_node(
        task_graph_mod.TaskNode(
            id="t2",
            agent="critic_agent",
            description="critic",
            inputs={"draft": "{{t1.result}}"},
            dependencies=["missing"],
            critical=True,
        )
    )

    core = reasoning_core.ReasoningCore()
    evaluated = await core.evaluate_plan(types.SimpleNamespace(objective="test objective"), {"input": "test"}, graph)

    assert evaluated["confidence"] < 0.75
    assert evaluated["strategy"]["safe_mode"] is True
    assert evaluated["simulation"]["status"] == "blocked"
    assert evaluated["critique"]["issues"]


def test_reasoning_core_enriches_nodes_with_fallbacks():
    _stub_core_engine()
    reasoning_core = importlib.import_module("backend.core.reasoning_core")
    task_graph_mod = importlib.import_module("backend.core.task_graph")

    graph = task_graph_mod.TaskGraph(
        nodes=[
            task_graph_mod.TaskNode(
                id="t1",
                agent="chat_agent",
                description="primary",
                inputs={},
            )
        ]
    )
    enriched = reasoning_core.ReasoningCore().enrich_for_resilience(graph)
    assert enriched.nodes[0].fallback_output["source"] == "reasoning_core"
    assert enriched.nodes[0].compensation_action == "log_failure:t1"


@pytest.mark.asyncio
async def test_reasoning_core_skips_for_low_complexity_single_node():
    _stub_core_engine()
    reasoning_core = importlib.import_module("backend.core.reasoning_core")
    task_graph_mod = importlib.import_module("backend.core.task_graph")

    graph = task_graph_mod.TaskGraph(
        nodes=[
            task_graph_mod.TaskNode(
                id="t1",
                agent="chat_agent",
                description="simple",
                inputs={"input": "hi"},
            )
        ]
    )

    evaluated = await reasoning_core.ReasoningCore().evaluate_plan(
        types.SimpleNamespace(objective="hi"),
        {"input": "hi", "intent": types.SimpleNamespace(complexity_level=0)},
        graph,
        decision=types.SimpleNamespace(complexity_score=0.1),
    )

    assert evaluated["strategy"]["reasoning_skipped"] is True
    assert evaluated["simulation"]["status"] == "skipped"
