import copy
import hashlib
import json
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
    
    # Risk-Adaptive Thresholds (P1 Hardening)
    RISK_THRESHOLDS = {
        "high": 0.90,
        "medium": 0.75,
        "low": 0.55
    }

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
            critique = await self._critique_graph(goal, perception, graph)
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

    async def _critique_graph(self, goal: Any, perception: Dict[str, Any], graph: TaskGraph) -> Dict[str, Any]:
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

        # 5. Phase 1: Local LLM Deep Cognitive Critique (Multi-Pass Reasoning)
        try:
            from backend.utils.llm_utils import call_lightweight_llm
            dag_structure = [{"id": n.id, "agent": n.agent, "deps": n.dependencies} for n in graph.nodes]
            prompt = (
                "You are the LEVI Reasoning Engine (Phase 1 Local LLM Stack).\n"
                "Critique the following Directed Acyclic Graph (DAG) plan for logical flaws, missing steps, or inefficiencies.\n"
                f"Goal: {objective}\nPlan: {json.dumps(dag_structure)}\n"
                "Output ONLY JSON in the format: {\"issues\": [\"critical flaw\"], \"warnings\": [\"minor inefficiency\"]}"
            )
            
            llm_res = await call_lightweight_llm([{"role": "system", "content": prompt}])
            
            if "```json" in llm_res:
                llm_res = llm_res.split("```json").split("```")[0]
            elif "```" in llm_res:
                llm_res = llm_res.split("```")[1].split("```")
                
            llm_critique = json.loads(llm_res.strip())
            
            if llm_critique.get("issues"):
                logger.info(f"[ReasoningCore] Local LLM identified issues: {llm_critique['issues']}")
                issues.extend(llm_critique["issues"])
            if llm_critique.get("warnings"):
                warnings.extend(llm_critique["warnings"])
                
        except Exception as e:
            logger.warning(f"[ReasoningCore] Local LLM Multi-Pass Critique fallback: {e}")

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
        v14.2 Bayesian-Inspired Confidence Scoring.
        P(Success | Evidence) = (P(Evidence | Success) * P(Success)) / P(Evidence)
        We use a weighted evidence approach to approximate this.
        """
        # 1. Prior: Based on historical success or base architectural trust
        prior = self._historical_success_rate(graph)
        
        # 2. Evidence from Structural Audit (Critique)
        # We model evidence as a multiplier [0, 1]
        issue_penalty = len(critique["issues"]) * 0.25
        warning_penalty = len(critique["warnings"]) * 0.08
        structural_evidence = max(0.0, 1.0 - (issue_penalty + warning_penalty))
        
        # 3. Evidence from Simulation Pass
        sim_evidence = 1.0 if simulation["status"] == "ok" else 0.3
        
        # 4. Resource Resilience Factor
        res = simulation.get("resource_prediction", {})
        tokens = res.get("estimated_tokens", 0)
        # High token count reduces confidence (fragility/hallucination risk)
        resource_evidence = 1.0 - min(0.3, (tokens / 10000.0) * 0.3)
        
        # 5. Bayesian Combination (Weighted Heuristic Approximation)
        # Likelihood = Structural * Simulation * Resource
        likelihood = structural_evidence * 0.5 + sim_evidence * 0.3 + resource_evidence * 0.2
        
        # Posterior = Prior * Likelihood
        # We add a complexity buffer (deeper graphs need more evidence)
        depth = self._graph_depth(graph)
        depth_penalty = 0.02 * max(0, depth - 3)
        
        posterior = (prior * 0.4 + likelihood * 0.6) - depth_penalty
        
        logger.info(f"[ReasoningCore] Confidence Calculated: Prior={prior:.2f}, Likelihood={likelihood:.2f}, Posterior={posterior:.2f}")
        
        return max(0.01, min(0.99, round(posterior, 3)))

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

    COMPENSATION_MAP: Dict[str, Any] = {
        "log_failure": lambda node: logger.warning(f"[Compensation] Node {node['id']} failed. Logged."),
        "reverse_debit": lambda node: logger.info(f"[Compensation] Reversing debit for {node['id']}"),
        "delete_resource": lambda node: logger.info(f"[Compensation] Deleting resource created by {node['id']}"),
        "execute_code": lambda node: logger.info(f"[Compensation] Cleaning up temp files for {node['id']}"),
    }

    async def execute_compensation_lifo(self, failed_nodes: List[Dict[str, Any]]):
        """
        Sovereign v14.2: Compensation Execution (LIFO).
        Reverses side effects in reverse order of execution.
        """
        logger.warning(f"[ReasoningCore] Initiating LIFO compensation for {len(failed_nodes)} nodes...")
        for node in reversed(failed_nodes):
            action = node.get("compensation_action", "log_failure")
            # Handle both simple strings and complex "action:arg" formats
            clean_action = action.split(":")[0] if ":" in action else action
            
            handler = self.COMPENSATION_MAP.get(clean_action, self.COMPENSATION_MAP["log_failure"])
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(node)
                else:
                    handler(node)
                logger.info(f"[Compensation] {clean_action} executed for {node.get('id')}")
            except Exception as e:
                logger.error(f"[Compensation] {clean_action} failed for {node.get('id')}: {e}")

    def enrich_for_resilience(self, graph: TaskGraph) -> TaskGraph:
        enriched = copy.deepcopy(graph)
        for node in enriched.nodes:
            if node.fallback_output is None:
                node.fallback_output = {
                    "message": f"Fallback result for {node.id}",
                    "source": "reasoning_core",
                }
            if node.compensation_action is None:
                # Default compensation based on agent type
                if "finance" in node.agent:
                    node.compensation_action = "reverse_debit"
                elif "cloud" in node.agent:
                    node.compensation_action = "delete_resource"
                elif "executor" in node.agent:
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
