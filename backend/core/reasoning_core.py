import copy
import hashlib
import logging
from typing import Any, Dict, List, Optional

from .task_graph import TaskGraph, TaskNode
from .evaluation.confidence_ml import confidence_model

logger = logging.getLogger(__name__)


class ReasoningCore:
    """
    Sovereign Reasoning Gate between planning and execution.
    Performs critique, simulation, and ML-based confidence scoring.
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
            
            # 🛡️ Graduation #13: Agentic Critique (Meta-Reasoning Bridge)
            if confidence < 0.7:
                logger.info(f"[ReasoningCore] Low confidence ({confidence}). Invoking Agentic Critique...")
                agentic_feedback = await self._invoke_agentic_critique(goal, graph)
                if agentic_feedback and not agentic_feedback.get("success", True):
                    critique["issues"].append(f"Agentic Critique: {agentic_feedback.get('feedback', 'Plan failed deep-logic validation.')}")
                    # Recalculate confidence after Agentic feedback
                    confidence = self._score_confidence(graph, critique, simulation, decision)

            strategy = self._select_execution_strategy(graph, critique, simulation, decision)

        enriched = copy.deepcopy(graph)
        enriched.metadata.update(
            {
                "reasoning_confidence": confidence,
                "reasoning_strategy": strategy,
                "critique": critique,
                "simulation": simulation,
                "passes": ["plan_generation", "plan_critique", "agentic_meta_critique" if confidence < 0.7 else None],
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

    async def _invoke_agentic_critique(self, goal: Any, graph: TaskGraph) -> Dict[str, Any]:
        """
        Calls the CriticAgent to perform high-fidelity audit of the proposed DAG.
        """
        try:
            from backend.agents.critic_agent import CriticAgent, CriticInput
            agent = CriticAgent()
            
            # Format graph for the critic
            graph_desc = "\n".join([f"- {node.id}: use {node.agent} to {node.objective}. Depends on: {node.dependencies}" for node in graph.nodes])
            
            payload = CriticInput(
                goal=getattr(goal, "objective", "unknown"),
                agent_output=f"Proposed Task Graph:\n{graph_desc}",
                context={"perception_mode": "architectural_validation"}
            )
            
            result = await agent._run(payload)
            return result
        except Exception as e:
            logger.error(f"[ReasoningCore] Agentic Critique failed: {e}")
            return {"success": True, "feedback": "Bridge failure"}

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

        # v14.1 On-Demand Force Flag
        if perception.get("force_reasoning") is True:
            logger.info("[ReasoningCore] Force reasoning flag detected.")
            return True

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
        """
        Sovereign v14.2 High-Fidelity Graph Critique.
        Checks for: Structural Integrity, Tool Sufficiency, and Logic Depth.
        """
        issues: List[str] = []
        warnings: List[str] = []
        node_ids = set()
        available = {node.id for node in graph.nodes}
        agent_types = {node.agent for node in graph.nodes}

        if not graph.nodes:
            issues.append("Planner produced an empty graph.")

        for node in graph.nodes:
            # 1. Structural Checks
            if node.id in node_ids:
                issues.append(f"Duplicate node id detected: {node.id}")
            node_ids.add(node.id)

            missing = [dep for dep in node.dependencies if dep not in available]
            if missing:
                issues.append(f"Node {node.id} has missing dependencies: {missing}")

            # 2. Resiliency Checks
            if not node.fallback_output and node.critical:
                warnings.append(f"Critical node {node.id} has no fallback output.")

            # 3. Cognitive Quality Checks
            if "research_agent" in agent_types and "search_agent" in agent_types:
                warnings.append("Potential logic redundancy: Both researcher and searcher active.")
            
            # Sub-graph depth check for complex queries
            if len(node.dependencies) > 4:
                warnings.append(f"Node {node.id} is a bottleneck with {len(node.dependencies)} dependencies.")

        objective = getattr(goal, "objective", "") or perception.get("input", "")
        
        # 4. Complexity Mismatch detection
        if objective and len(graph.nodes) == 1 and len(objective.split()) > 18:
            warnings.append("Single-node plan for a high-context objective may be too shallow.")
            # Trigger harder penalty if it's very shallow
            if len(objective.split()) > 40:
                issues.append("Plan is critically shallow for the provided context complexity.")

        return {
            "issues": issues, 
            "warnings": warnings, 
            "goal": objective,
            "agent_diversity": len(agent_types)
        }

    def _simulate_graph(self, graph: TaskGraph) -> Dict[str, Any]:
        """
        Sovereign v14.2 Simulation Pass with Resource Prediction.
        """
        produced: Dict[str, str] = {}
        unresolved: List[str] = []
        order: List[List[Dict[str, Any]]] = []
        
        total_predicted_tokens = 0
        vram_est_mb = 0

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
                
                # Dynamic Resource Prediction
                node_tokens = 500 if "research" in node.agent else 200
                total_predicted_tokens += node_tokens
                if "imaging" in node.agent or "video" in node.agent:
                    vram_est_mb += 2048
                
                layer.append(
                    {
                        "node_id": node.id,
                        "agent": node.agent,
                        "depends_on": list(node.dependencies),
                        "predicted_tokens": node_tokens
                    }
                )
                del pending[node.id]
            
            order.append(layer)

        return {
            "status": "ok" if not unresolved else "blocked",
            "unresolved_nodes": unresolved,
            "dry_run": order,
            "resource_prediction": {
                "estimated_tokens": total_predicted_tokens,
                "vram_mb": vram_est_mb,
                "concurrency_max": max((len(layer) for layer in order), default=0)
            }
        }

    def _score_confidence(
        self,
        graph: TaskGraph,
        critique: Dict[str, Any],
        simulation: Dict[str, Any],
        decision: Optional[Any],
    ) -> float:
        """
        v14.2 High-Fidelity Confidence Scoring.
        Now factors in resource prediction and agent diversity.
        """
        res = simulation.get("resource_prediction", {})
        features = {
            "depth": float(self._graph_depth(graph)),
            "node_count": float(len(graph.nodes)),
            "agent_diversity": float(critique.get("agent_diversity", 1)),
            "est_tokens": float(res.get("estimated_tokens", 0)),
            "issue_count": float(len(critique["issues"])),
            "warning_count": float(len(critique["warnings"])),
            "sim_blocked": 1.0 if simulation["status"] != "ok" else 0.0
        }
        
        # Base score starts from simulation status
        score = 0.9 if simulation["status"] == "ok" else 0.4
        
        # Penalties
        score -= (features["issue_count"] * 0.15)
        score -= (features["warning_count"] * 0.05)
        
        # Penalty for excessive resource usage (Fragility risk)
        if features["est_tokens"] > 5000:
            score -= 0.1
        
        # Complexity Reward for multi-node planning success
        if features["node_count"] > 2 and simulation["status"] == "ok":
            score += 0.05
            
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
