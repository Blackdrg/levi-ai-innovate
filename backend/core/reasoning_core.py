import copy
import hashlib
import logging
from typing import Any, Dict, List, Optional

from .task_graph import TaskGraph, TaskNode

logger = logging.getLogger(__name__)


class ReasoningCore:
    """
    Mandatory reasoning gate between planning and execution.
    Performs critique, simulation, and execution strategy selection.
    """

    MIN_CONFIDENCE = 0.55
    COMPLEXITY_SKIP_THRESHOLD = 0.35

    async def evaluate_plan(
        self,
        goal: Any,
        perception: Dict[str, Any],
        graph: TaskGraph,
        decision: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if not self.should_activate(perception, decision, graph):
            critique = {"issues": [], "warnings": [], "goal": getattr(goal, "objective", ""), "skipped": True}
            simulation = {
                "status": "skipped",
                "unresolved_nodes": [],
                "dry_run": [],
                "reason": "task_complexity_below_threshold",
            }
            confidence = self._score_confidence(graph, critique, simulation, decision)
            strategy = self._select_execution_strategy(graph, critique, simulation, decision)
            strategy["reasoning_skipped"] = True
        else:
            critique = self._critique_graph(goal, perception, graph)
            simulation = self._simulate_graph(graph)
            confidence = self._score_confidence(graph, critique, simulation, decision)
            strategy = self._select_execution_strategy(graph, critique, simulation, decision)

        enriched = copy.deepcopy(graph)
        enriched.metadata.update(
            {
                "reasoning_confidence": confidence,
                "reasoning_strategy": strategy,
                "critique": critique,
                "simulation": simulation,
                "passes": ["plan_generation", "plan_critique"],
                "graph_signature": self.graph_signature(graph),
                "reasoning_active": not strategy.get("reasoning_skipped", False),
            }
        )
        return {
            "graph": enriched,
            "critique": critique,
            "simulation": simulation,
            "confidence": confidence,
            "strategy": strategy,
        }

    @staticmethod
    def graph_signature(graph: TaskGraph) -> str:
        material = "|".join(
            f"{node.id}:{node.agent}:{','.join(node.dependencies)}" for node in graph.nodes
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def should_activate(
        self,
        perception: Dict[str, Any],
        decision: Optional[Any],
        graph: TaskGraph,
    ) -> bool:
        if perception.get("fast_path_bypass") is True:
            return False

        # v14.1 Strict Triggers
        is_sensitive = perception.get("intent", {}).is_sensitive if hasattr(perception.get("intent"), "is_sensitive") else False
        if is_sensitive:
            logger.info("[ReasoningCore] Sensitivity trigger: Activating reasoning.")
            return True

        complexity = self._compute_complexity_score(perception, decision, graph)

        # Only activate if complexity is high enough or DAG is deep
        if complexity >= self.COMPLEXITY_SKIP_THRESHOLD:
            return True
            
        if len(graph.nodes) > 3: # Always reason about complex multi-step DAGs
            return True
            
        return False

    def _compute_complexity_score(self, perception: Dict[str, Any], decision: Optional[Any], graph: TaskGraph) -> float:
        """
        v14.1 Complexity Scoring System.
        Weights: Intent Type (40%), Input Length (20%), Tool Diversity (20%), DAG Shape (20%).
        """
        score = 0.0
        
        # 1. Intent Weight (40%)
        intent = perception.get("intent")
        if intent:
            # Scale intent complexity (0-3) to 0.0-1.0
            score += (intent.complexity_level / 3.0) * 0.4
        
        # 2. Input Length Weight (20%)
        user_input = perception.get("input", "")
        word_count = len(str(user_input).split())
        score += min(1.0, word_count / 30.0) * 0.2
        
        # 3. Tool Diversity (20%)
        unique_agents = len({node.agent for node in graph.nodes})
        score += min(1.0, unique_agents / 4.0) * 0.2
        
        # 4. DAG Shape (20%)
        depth = self._graph_depth(graph)
        score += min(1.0, depth / 5.0) * 0.2
        
        return round(score, 3)

    def _extract_complexity(self, perception: Dict[str, Any], decision: Optional[Any]) -> float:
        """Legacy compatibility wrapper."""
        return self._compute_complexity_score(perception, decision, TaskGraph())

    def _critique_graph(self, goal: Any, perception: Dict[str, Any], graph: TaskGraph) -> Dict[str, Any]:
        issues: List[str] = []
        warnings: List[str] = []
        node_ids = set()
        available = {node.id for node in graph.nodes}

        if not graph.nodes:
            issues.append("Planner produced an empty graph.")

        for node in graph.nodes:
            if node.id in node_ids:
                issues.append(f"Duplicate node id detected: {node.id}")
            node_ids.add(node.id)

            missing = [dep for dep in node.dependencies if dep not in available]
            if missing:
                issues.append(f"Node {node.id} has missing dependencies: {missing}")

            if not node.fallback_output and node.critical:
                warnings.append(f"Critical node {node.id} has no fallback output.")

            if not node.compensation_action and node.critical:
                warnings.append(f"Critical node {node.id} has no compensation action.")

        objective = getattr(goal, "objective", "") or perception.get("input", "")
        if objective and len(graph.nodes) == 1 and len(objective.split()) > 18:
            warnings.append("Single-node plan for a high-context objective may be too shallow.")

        return {"issues": issues, "warnings": warnings, "goal": objective}

    def _simulate_graph(self, graph: TaskGraph) -> Dict[str, Any]:
        produced: Dict[str, str] = {}
        unresolved: List[str] = []
        order: List[List[Dict[str, Any]]] = []

        pending = {node.id: node for node in graph.nodes}

        while pending:
            ready = [
                node for node_id, node in pending.items()
                if all(dep in produced for dep in node.dependencies)
            ]

            if not ready:
                unresolved.extend(pending.keys())
                break
            
            layer = []
            for node in ready:
                mock_output = f"simulated:{node.agent}:{node.id}"
                produced[node.id] = mock_output
                layer.append(
                    {
                        "node_id": node.id,
                        "agent": node.agent,
                        "depends_on": list(node.dependencies),
                        "mock_output": mock_output,
                    }
                )
                del pending[node.id]
            
            order.append(layer)

        return {
            "status": "ok" if not unresolved else "blocked",
            "unresolved_nodes": unresolved,
            "dry_run": order,
        }

    def _score_confidence(
        self,
        graph: TaskGraph,
        critique: Dict[str, Any],
        simulation: Dict[str, Any],
        decision: Optional[Any],
    ) -> float:
        score = 0.92
        depth = self._graph_depth(graph)
        dependency_complexity = sum(len(node.dependencies) for node in graph.nodes)
        historical_success = self._historical_success_rate(graph)
        score -= 0.2 * len(critique["issues"])
        score -= 0.05 * len(critique["warnings"])
        if simulation["status"] not in {"ok", "skipped"}:
            score -= 0.2
        score -= min(0.2, max(0, depth - 2) * 0.04)
        score -= min(0.12, dependency_complexity * 0.02)
        score -= max(0.0, 0.8 - historical_success) * 0.15
        if decision and getattr(decision, "complexity_score", 0.0) > 0.8:
            score -= 0.05
        return max(0.05, min(0.99, round(score, 3)))

    def _select_execution_strategy(
        self,
        graph: TaskGraph,
        critique: Dict[str, Any],
        simulation: Dict[str, Any],
        decision: Optional[Any],
    ) -> Dict[str, Any]:
        depth = self._graph_depth(graph)
        dependency_complexity = sum(len(node.dependencies) for node in graph.nodes)
        historical_success = self._historical_success_rate(graph)
        safe_mode = bool(
            critique["issues"]
            or simulation["status"] not in {"ok", "skipped"}
            or depth >= 5
            or dependency_complexity >= 5
            or historical_success < 0.65
        )
        mode = getattr(getattr(decision, "mode", None), "value", "BALANCED")
        return {
            "mode": mode,
            "safe_mode": safe_mode,
            "execution_style": "linear" if safe_mode else "dag",
            "requires_refinement": bool(critique["issues"] or (safe_mode and simulation["status"] != "skipped") or len(critique["warnings"]) >= 2),
            "historical_success_rate": historical_success,
            "dependency_complexity": dependency_complexity,
            "dag_depth": depth,
        }

    def enrich_for_resilience(self, graph: TaskGraph) -> TaskGraph:
        enriched = copy.deepcopy(graph)
        for node in enriched.nodes:
            if node.fallback_output is None:
                node.fallback_output = {
                    "message": f"Fallback result for {node.id}",
                    "source": "reasoning_core",
                }
            if node.compensation_action is None:
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

    def _historical_success_rate(self, graph: TaskGraph) -> float:
        learned = graph.metadata.get("learned_strategy", {}) or {}
        avg = learned.get("avg_fidelity")
        if avg is None:
            return 0.8
        try:
            return max(0.05, min(0.99, float(avg)))
        except (TypeError, ValueError):
            return 0.8

    def _extract_complexity(self, perception: Dict[str, Any], decision: Optional[Any]) -> float:
        if decision is not None and getattr(decision, "complexity_score", None) is not None:
            return float(getattr(decision, "complexity_score", 0.0))
        intent = perception.get("intent")
        if intent is not None and getattr(intent, "complexity_level", None) is not None:
            return min(1.0, max(0.0, float(intent.complexity_level) / 3.0))
        user_input = perception.get("input", "")
        return min(1.0, len(str(user_input).split()) / 20.0)
