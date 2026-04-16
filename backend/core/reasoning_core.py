import asyncio
import copy
import logging
from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np

from backend.core.agent_registry import AgentRegistry
from backend.core.task_graph import TaskGraph

logger = logging.getLogger(__name__)


class BeliefNetwork:
    """Small Bayesian-style belief network used for explainable plan audits."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.beliefs: Dict[str, float] = {}
        self.evidence: Dict[str, float] = {}

    def add_proposition(self, name: str, prior: float = 0.5):
        self.graph.add_node(name, prior=float(prior))
        self.beliefs[name] = float(prior)

    def add_causality(self, cause: str, effect: str, strength: float):
        self.graph.add_edge(cause, effect, weight=float(max(0.0, min(1.0, strength))))

    def reset(self):
        self.evidence.clear()
        self.beliefs = {
            node: float(self.graph.nodes[node].get("prior", 0.5))
            for node in self.graph.nodes()
        }

    def observe(self, proposition: str, is_true: bool):
        value = 1.0 if is_true else 0.0
        self.evidence[proposition] = value
        self.beliefs[proposition] = value

    def propagate(self, iterations: int = 5):
        for _ in range(iterations):
            new_beliefs: Dict[str, float] = {}
            for node in self.graph.nodes():
                if node in self.evidence:
                    new_beliefs[node] = self.evidence[node]
                    continue

                parents = list(self.graph.predecessors(node))
                if not parents:
                    new_beliefs[node] = self.beliefs.get(node, self.graph.nodes[node].get("prior", 0.5))
                    continue

                influences = [
                    self.beliefs.get(parent, 0.5) * float(self.graph[parent][node].get("weight", 0.5))
                    for parent in parents
                ]
                combined = float(np.mean(influences)) if influences else 0.5
                prior = self.beliefs.get(node, self.graph.nodes[node].get("prior", 0.5))
                alpha = 0.3
                new_beliefs[node] = max(0.0, min(1.0, ((1 - alpha) * prior) + (alpha * combined)))
            self.beliefs = new_beliefs

    def query(self, proposition: str) -> float:
        return float(self.beliefs.get(proposition, 0.5))

    def get_all_beliefs(self) -> Dict[str, float]:
        return {k: round(v, 4) for k, v in self.beliefs.items()}


class ReasoningCore:
    """Bayesian reasoning gate between planning and execution."""

    MIN_CONFIDENCE = 0.65
    COMPLEXITY_SKIP_THRESHOLD = 0.35

    COMPENSATION_MAP: Dict[str, Any] = {
        "log_failure": lambda node: logger.warning("[Compensation] Node %s failed. Logged.", node.get("id")),
        "reverse_debit": lambda node: logger.info("[Compensation] Reversing debit for %s", node.get("id")),
        "delete_resource": lambda node: logger.info("[Compensation] Deleting resource created by %s", node.get("id")),
        "execute_code": lambda node: logger.info("[Compensation] Cleaning up execution artefacts for %s", node.get("id")),
    }

    def __init__(self):
        self.belief_network = BeliefNetwork()
        self._initialize_default_beliefs()

    def _initialize_default_beliefs(self):
        self.belief_network.add_proposition("has_sufficient_context", 0.5)
        self.belief_network.add_proposition("plan_is_logical", 0.5)
        self.belief_network.add_proposition("plan_is_safe", 0.7)
        self.belief_network.add_proposition("can_execute", 0.6)
        self.belief_network.add_proposition("mission_achievable", 0.5)

        self.belief_network.add_causality("has_sufficient_context", "plan_is_logical", 0.8)
        self.belief_network.add_causality("plan_is_logical", "mission_achievable", 0.7)
        self.belief_network.add_causality("plan_is_safe", "mission_achievable", 0.6)
        self.belief_network.add_causality("can_execute", "mission_achievable", 0.8)

    async def audit_plan(self, plan_dag: Any) -> Dict[str, Any]:
        dag = self._graph_to_dict(plan_dag)
        self.belief_network.reset()

        has_context = len(dag.get("nodes", [])) > 0
        is_logical = self._check_logical_structure(dag)
        is_safe = self._check_safety_constraints(dag)
        can_execute = self._check_executability(dag)

        self.belief_network.observe("has_sufficient_context", has_context)
        self.belief_network.observe("plan_is_logical", is_logical)
        self.belief_network.observe("plan_is_safe", is_safe)
        self.belief_network.observe("can_execute", can_execute)
        self.belief_network.propagate(iterations=5)

        achievability = self.belief_network.query("mission_achievable")
        recommendation = "APPROVE" if achievability > 0.75 else "REFINE" if achievability > 0.50 else "REJECT"
        issues: List[str] = []
        warnings: List[str] = []
        if not has_context:
            issues.append("Plan contains no executable nodes.")
        if not is_logical:
            issues.append("Plan graph is structurally invalid or cyclic.")
        if not is_safe:
            issues.append("Plan violates safety constraints.")
        if not can_execute:
            issues.append("Plan references unavailable agents.")
        if recommendation == "REFINE" and not issues:
            warnings.append("Plan is plausible but confidence is not yet strong.")

        return {
            "is_valid": achievability > self.MIN_CONFIDENCE,
            "confidence": round(achievability, 4),
            "beliefs": self.belief_network.get_all_beliefs(),
            "recommendation": recommendation,
            "issues": issues,
            "warnings": warnings,
        }

    async def evaluate_plan(
        self,
        goal: Any,
        perception: Dict[str, Any],
        graph: TaskGraph,
        decision: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if not self.should_activate(perception, decision, graph):
            confidence = max(0.55, min(0.75, 0.55 + (self._extract_complexity(perception, decision) * 0.2)))
            critique = {
                "issues": [],
                "warnings": [],
                "goal": getattr(goal, "objective", perception.get("input", "")),
                "beliefs": {},
                "recommendation": "APPROVE",
                "skipped": True,
            }
            simulation = {"status": "skipped", "success_probability": confidence, "failure_modes": {}, "avg_latency_ms": 0.0}
            strategy = await self._select_execution_strategy(graph, critique, simulation, decision, confidence)
            strategy["reasoning_skipped"] = True
            enriched = copy.deepcopy(graph)
            enriched.metadata.update({
                "reasoning_confidence": confidence,
                "reasoning_strategy": strategy,
                "critique": critique,
                "simulation": simulation,
                "graph_signature": self.graph_signature(graph),
                "reasoning_active": False,
            })
            return {"graph": enriched, "critique": critique, "simulation": simulation, "confidence": confidence, "strategy": strategy}

        audit = await self.audit_plan(graph)
        critique = {
            "issues": audit["issues"],
            "warnings": audit["warnings"],
            "goal": getattr(goal, "objective", perception.get("input", "")),
            "beliefs": audit["beliefs"],
            "recommendation": audit["recommendation"],
            "skipped": False,
        }
        simulation = {
            "status": "ok" if audit["is_valid"] else "blocked",
            "success_probability": audit["confidence"],
            "failure_modes": {issue: 1 for issue in audit["issues"]},
            "avg_latency_ms": 0.0,
        }
        confidence = audit["confidence"]
        strategy = await self._select_execution_strategy(graph, critique, simulation, decision, confidence)

        enriched = copy.deepcopy(graph)
        enriched.metadata.update(
            {
                "reasoning_confidence": confidence,
                "reasoning_strategy": strategy,
                "critique": critique,
                "simulation": simulation,
                "graph_signature": self.graph_signature(graph),
                "reasoning_active": True,
            }
        )
        return {"graph": enriched, "critique": critique, "simulation": simulation, "confidence": confidence, "strategy": strategy}

    @staticmethod
    def graph_signature(graph: TaskGraph) -> str:
        import hashlib
        material = "|".join(
            f"{node.id}:{node.agent}:{','.join(node.dependencies)}" for node in graph.nodes
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def should_activate(self, perception: Dict[str, Any], decision: Optional[Any], graph: TaskGraph) -> bool:
        if perception.get("fast_path_bypass") is True:
            return False
        if perception.get("force_reasoning") is True:
            return True
        if len(graph.nodes) > 1:
            return True
        return self._extract_complexity(perception, decision) >= self.COMPLEXITY_SKIP_THRESHOLD

    async def _select_execution_strategy(
        self,
        graph: TaskGraph,
        critique: Dict[str, Any],
        simulation: Dict[str, Any],
        decision: Optional[Any],
        confidence: float,
    ) -> Dict[str, Any]:
        depth = self._graph_depth(graph)
        dependency_complexity = sum(len(node.dependencies) for node in graph.nodes)
        safe_mode = bool(
            critique["issues"]
            or confidence < self.MIN_CONFIDENCE
            or simulation.get("status") not in {"ok", "skipped"}
            or depth >= 5
            or dependency_complexity >= 6
        )
        mode = getattr(getattr(decision, "mode", None), "value", "BALANCED")
        return {
            "mode": mode,
            "safe_mode": safe_mode,
            "execution_style": "linear" if safe_mode else "dag",
            "requires_refinement": bool(critique["issues"] or critique["warnings"] or confidence < 0.75),
            "historical_success_rate": round(confidence, 3),
            "dependency_complexity": dependency_complexity,
            "dag_depth": depth,
        }

    async def execute_compensation_lifo(self, failed_nodes: List[Dict[str, Any]]):
        logger.warning("[ReasoningCore] Initiating LIFO compensation for %s nodes...", len(failed_nodes))
        for node in reversed(failed_nodes):
            action = node.get("compensation_action", "log_failure")
            clean_action = action.split(":")[0] if ":" in action else action
            handler = self.COMPENSATION_MAP.get(clean_action, self.COMPENSATION_MAP["log_failure"])
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(node)
                else:
                    handler(node)
            except Exception as exc:
                logger.error("[Compensation] %s failed for %s: %s", clean_action, node.get("id"), exc)

    def enrich_for_resilience(self, graph: TaskGraph) -> TaskGraph:
        enriched = copy.deepcopy(graph)
        for node in enriched.nodes:
            if node.fallback_output is None:
                node.fallback_output = {"message": f"Fallback result for {node.id}", "source": "reasoning_core"}
            if node.compensation_action is None:
                if "finance" in node.agent:
                    node.compensation_action = "reverse_debit"
                elif "cloud" in node.agent:
                    node.compensation_action = "delete_resource"
                elif "executor" in node.agent or "code" in node.agent:
                    node.compensation_action = "execute_code"
                else:
                    node.compensation_action = f"log_failure:{node.id}"
        return enriched

    def _graph_depth(self, graph: TaskGraph) -> int:
        depth_cache: Dict[str, int] = {}
        nodes_map = {node.id: node for node in graph.nodes}

        def depth(node_id: str) -> int:
            if node_id in depth_cache:
                return depth_cache[node_id]
            node = nodes_map.get(node_id)
            if not node or not node.dependencies:
                depth_cache[node_id] = 1
                return 1
            depth_cache[node_id] = 1 + max(depth(dep) for dep in node.dependencies)
            return depth_cache[node_id]

        return max((depth(node.id) for node in graph.nodes), default=1)

    def _extract_complexity(self, perception: Dict[str, Any], decision: Optional[Any]) -> float:
        if decision is not None and getattr(decision, "complexity_score", None) is not None:
            return float(getattr(decision, "complexity_score", 0.0))
        intent = perception.get("intent")
        if intent is not None and hasattr(intent, "complexity_level"):
            return min(1.0, max(0.0, float(intent.complexity_level) / 3.0))
        user_input = perception.get("input", "")
        return min(1.0, len(str(user_input).split()) / 20.0)

    def _graph_to_dict(self, plan_dag: Any) -> Dict[str, Any]:
        if isinstance(plan_dag, TaskGraph):
            nodes = [
                {
                    "id": node.id,
                    "agent": node.agent,
                    "description": node.description,
                    "dependencies": list(node.dependencies),
                    "metadata": dict(node.metadata),
                }
                for node in plan_dag.nodes
            ]
            edges = [(dep, node.id) for node in plan_dag.nodes for dep in node.dependencies]
            return {"nodes": nodes, "edges": edges}
        if isinstance(plan_dag, dict):
            if "edges" not in plan_dag:
                nodes = plan_dag.get("nodes", [])
                plan_dag = dict(plan_dag)
                plan_dag["edges"] = [
                    (dep, node.get("id"))
                    for node in nodes
                    for dep in node.get("dependencies", [])
                    if node.get("id")
                ]
            return plan_dag
        return {"nodes": [], "edges": []}

    def _check_logical_structure(self, plan_dag: Dict[str, Any]) -> bool:
        nodes = plan_dag.get("nodes", [])
        edges = plan_dag.get("edges", [])
        if not nodes:
            return False
        graph = nx.DiGraph()
        for node in nodes:
            node_id = node.get("id")
            if node_id:
                graph.add_node(node_id)
        graph.add_edges_from(edges)
        try:
            list(nx.topological_sort(graph))
            return True
        except nx.NetworkXUnfeasible:
            return False

    def _check_safety_constraints(self, plan_dag: Dict[str, Any]) -> bool:
        forbidden_patterns = ["delete_user_data", "expose_credentials", "network_exfiltration", "drop_table", "rm -rf /"]
        plan_str = str(plan_dag).lower()
        return not any(pattern in plan_str for pattern in forbidden_patterns)

    def _check_executability(self, plan_dag: Dict[str, Any]) -> bool:
        for node in plan_dag.get("nodes", []):
            agent_id = str(node.get("agent", "")).strip()
            if not agent_id:
                return False
            normalized = agent_id.lower().replace("agent", "").replace("_", "").strip()
            candidates = [
                agent_id,
                agent_id.lower(),
                normalized,
                f"{normalized}_agent",
            ]
            if any(AgentRegistry.get_agent(candidate) for candidate in candidates):
                continue
            if agent_id.lower() in {"graphexecutor", "graphexecutor"}:
                continue
            return False
        return True


reasoning_core = ReasoningCore()
