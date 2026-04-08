from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .orchestrator_types import BrainDecision, BrainMode, ExecutionBudget, ExecutionPolicy, LLMPolicy, MemoryPolicy, ToolResult

logger = logging.getLogger(__name__)


def bridge_policy(policy: Any) -> BrainDecision:
    try:
        mode = BrainMode(policy.mode)
    except ValueError:
        mode = BrainMode.BALANCED

    policy_enable = dict(getattr(policy, "enable", {}) or {})
    execution_payload = dict(getattr(policy, "execution", {}) or {})
    memory_payload = dict(getattr(policy, "memory", {}) or {})
    llm_payload = dict(getattr(policy, "llm", {}) or {})
    budget_payload = dict(execution_payload.get("budget", {}) or {})

    return BrainDecision(
        mode=mode,
        enable_agents={
            "planner": True,
            "critic": False,
            "retrieval": False,
            "browser": False,
            "docker": False,
            **policy_enable,
        },
        memory_policy=MemoryPolicy(
            redis=memory_payload.get("redis", True),
            postgres=memory_payload.get("postgres", True),
            neo4j=memory_payload.get("neo4j", False),
            faiss=memory_payload.get("faiss", True),
        ),
        execution_policy=ExecutionPolicy(
            parallel_waves=execution_payload.get("parallel_waves", 2),
            max_retries=execution_payload.get("max_retries", 1),
            sandbox_required=policy_enable.get("sandbox", False),
            retry_strategy=execution_payload.get("retry_strategy", "exp_backoff_jitter"),
            budget=ExecutionBudget(**budget_payload) if budget_payload else ExecutionBudget(),
        ),
        llm_policy=LLMPolicy(
            local_only=llm_payload.get("local_only", True),
            cloud_fallback=llm_payload.get("fallback_allowed", False),
        ),
        complexity_score=getattr(policy, "model_dump", lambda: {})().get("scores", {}).get("complexity_score", 0.5),
    )


def validate_workflow_integrity(
    request_id: str,
    perception: Dict[str, Any],
    goal: Any,
    task_graph: Any,
    results: List[ToolResult],
    memory_event: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    warnings: List[str] = []
    if not perception.get("intent"):
        warnings.append("missing_intent")
    if not getattr(goal, "objective", None):
        warnings.append("missing_goal")
    if not getattr(task_graph, "nodes", []):
        warnings.append("empty_graph")
    if not results:
        warnings.append("empty_results")
    if memory_event is None:
        warnings.append("memory_not_persisted")
    workflow = {
        "request_id": request_id,
        "stages": [
            "gateway",
            "orchestrator",
            "perception",
            "goal",
            "planner",
            "reasoning",
            "executor",
            "agents",
            "memory",
            "response",
        ],
        "node_count": len(getattr(task_graph, "nodes", [])),
        "result_count": len(results),
        "warnings": warnings,
        "healthy": not warnings or warnings == ["memory_not_persisted"],
    }
    if warnings:
        logger.warning("[Workflow] Integrity warnings for %s: %s", request_id, warnings)
    return workflow
