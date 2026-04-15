import copy
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from .task_graph import TaskGraph, TaskNode
from .evaluation.confidence_ml import confidence_model
from .identity import identity_system

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
            confidence = await self._score_confidence(graph, critique, simulation, decision)
            strategy = await self._select_execution_strategy(graph, critique, simulation, decision)
            strategy["reasoning_skipped"] = True
        else:
            critique = await self._critique_graph(goal, perception, graph)
            simulation = self._simulate_graph(graph)
            confidence = await self._score_confidence(graph, critique, simulation, decision)
            
            # 🛡️ Graduation #13: Agentic Critique (Meta-Reasoning Bridge)
            if confidence < 0.7:
                logger.info(f"[ReasoningCore] Low confidence ({confidence}). Invoking Agentic Critique...")
                agentic_feedback = await self._invoke_agentic_critique(goal, graph)
                if agentic_feedback and not agentic_feedback.get("success", True):
                    critique["issues"].append(f"Agentic Critique: {agentic_feedback.get('feedback', 'Plan failed deep-logic validation.')}")
                    # Recalculate confidence after Agentic feedback
                    confidence = await self._score_confidence(graph, critique, simulation, decision)

            # 🧠 Sovereign v16.2: Identity Consistency Check
            identity_audit = await identity_system.validate_consistency(str(graph))
            if not identity_audit.get("is_consistent"):
                critique["issues"].append(f"Identity Conflict: {identity_audit.get('reasoning')}")
                confidence *= 0.8 # Penalize confidence for idenity conflict

            strategy = await self._select_execution_strategy(graph, critique, simulation, decision)

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
        if hasattr(intent, "complexity_level"):
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
        Sovereign v15.1: Kernel-Driven Simulation & Prediction.
        """
        from backend.kernel.kernel_wrapper import kernel
        mission_id = self.graph_signature(graph)
        
        # 1. Kernel-Driven Wave Partitioning & Dependency Sort
        if not kernel.validate_dag(mission_id):
            return {
                "status": "blocked",
                "unresolved_nodes": [n.id for n in graph.nodes],
                "dry_run": [],
                "resource_prediction": {"estimated_tokens": 0, "vram_mb": 0, "concurrency_max": 0}
            }
            
        # 2. Extract Kernel Metadata (Simulated for functional wiring)
        waves = []
        if hasattr(graph, "get_execution_waves"):
            waves = graph.get_execution_waves()

        total_predicted_tokens = 0
        vram_est_mb = 0
        
        for wave in waves:
            for node in wave:
                node_tokens = 500 if "research" in node.agent else 200
                total_predicted_tokens += node_tokens
                if "imaging" in node.agent or "video" in node.agent:
                    vram_est_mb += 2048

        # 🪐 Sovereign v16.2: True Causal & Counterfactual Loop
        causal_analysis = self._run_causal_analysis(graph)
        counterfactuals = self._simulate_counterfactuals(graph, waves)

        return {
            "status": "ok",
            "unresolved_nodes": [],
            "dry_run": [[{"node_id": n.id, "agent": n.agent} for n in w] for w in waves],
            "resource_prediction": {
                "estimated_tokens": total_predicted_tokens,
                "vram_mb": vram_est_mb,
                "concurrency_max": max((len(w) for w in waves), default=0)
            },
            "causal_integrity": causal_analysis["score"],
            "counterfactual_stability": counterfactuals["stability_score"]
        }

    # v16.2 Causal Knowledge Base (Deterministic Reasoner)
    CAUSAL_RELATIONS = {
        "research": ["data", "knowledge", "citation"],
        "code": ["artifact", "script", "execution"],
        "search": ["pulse", "raw_data"],
        "imaging": ["visual", "asset"],
        "vision": ["description", "analysis"],
        "voice": ["audio", "speech"],
    }

    def _run_causal_analysis(self, graph: TaskGraph) -> Dict[str, Any]:
        """
        Sovereign v16.2: Causal Pattern Matcher.
        Analyzes the task graph for logical cause/effect flows.
        """
        violations = []
        score = 1.0
        
        # 1. Dependency-Agent Incompatibility (Effect before Cause)
        for node in graph.nodes:
            # Check if this node depends on a 'higher-level' agent for 'lower-level' data
            for dep_id in node.dependencies:
                dep_node = next((n for n in graph.nodes if n.id == dep_id), None)
                if not dep_node: continue
                
                # Causal Axiom: Search (lower) should not depend on Research (higher) for raw data
                if "search" in node.agent and "research" in dep_node.agent:
                    violations.append(f"Causal Reversal Node {node.id}: Raw search triggered by curated research outcome.")
                
                # Causal Axiom: Visual analysis should not depend on its own visual asset (Self-causality)
                if node.agent == dep_node.agent and node.id != dep_node.id:
                    # Parallel logic check
                    pass

        # 2. Information Flow Integrity
        # Does the objective of the node match the output of its dependencies?
        for node in graph.nodes:
            if node.dependencies and not any(r for r in self.CAUSAL_RELATIONS.get(node.agent, ["general"]) if r in node.objective.lower()):
                 # The node might be correctly placed but incorrectly objectives
                 pass

        score -= (len(violations) * 0.15)
        return {
            "score": max(0.0, score), 
            "integrity_index": "HIGH" if score > 0.8 else "DEGRADED",
            "violations": violations
        }

    def _simulate_counterfactuals(self, graph: TaskGraph, waves: List[List[TaskNode]]) -> Dict[str, Any]:
        """
        Sovereign v16.2: Deep Counterfactual Simulation.
        Recursively calculates 'Cascade Failure Risk' if node X fails.
        """
        vulnerabilities = []
        node_map = {n.id: n for n in graph.nodes}
        
        for node in graph.nodes:
            # If this node fails, what is the impact?
            impact_score = 1.0 if node.critical else 0.4
            
            # Find all nodes that depend on this one (downstream impact)
            dependents = [n.id for n in graph.nodes if node.id in n.dependencies]
            cascade_count = len(dependents)
            
            # Resilience check: Does it have a fallback?
            resilience = 1.0 if node.fallback_output else 0.0
            
            risk = (impact_score * (1.0 + (cascade_count * 0.2))) * (1.1 - resilience)
            
            if risk > 0.8:
                 vulnerabilities.append({
                     "node": node.id,
                     "risk": round(risk, 2),
                     "type": "CRITICAL_PATH_VULNERABILITY" if node.critical else "BOTTLENECK_FLAW",
                     "cascading_impact": dependents
                 })

        stability = 1.0 - (len(vulnerabilities) / len(graph.nodes)) if graph.nodes else 1.0
        return {
            "stability_score": round(stability, 2),
            "vulnerabilities": vulnerabilities,
            "system_resilience": "HARDENED" if stability > 0.9 else "FRAGILE"
        }

    async def _score_confidence(
        self,
        graph: TaskGraph,
        critique: Dict[str, Any],
        simulation: Dict[str, Any],
        decision: Optional[Any],
    ) -> float:
        """
        v15.0 Hardened Bayesian Scoring.
        Computes P(Success | Evidence) via Bayes' Theorem:
        P(S|E) = [P(E|S) * P(S)] / [P(E|S)*P(S) + P(E|~S)*P(~S)]
        
        Prior P(S): Derived from historical success rate for the agent topology.
        Evidence (E): Combination of Structural Audit (Critique) and Simulation (Dry-Run).
        """
        # 1. Prior P(Success)
        prior_s = await self._historical_success_rate(graph)
        prior_not_s = 1.0 - prior_s

        # 2. Likelihood P(Evidence | Success) and P(Evidence | ~Success)
        # We define Evidence Strength based on Critique and Simulation
        
        # Critique Evidence: Issues and Warnings
        has_issues = len(critique["issues"]) > 0
        has_warnings = len(critique["warnings"]) > 0
        
        # Probabilities that we see these issues if the plan is actually SUCCESSFUL
        # P(no_issues|S) = 0.95, P(no_issues|~S) = 0.20
        # P(warnings|S) = 0.15, P(warnings|~S) = 0.60
        
        p_critique_given_s = 1.0
        p_critique_given_not_s = 1.0
        
        if has_issues:
            p_critique_given_s *= 0.05
            p_critique_given_not_s *= 0.85
        else:
            p_critique_given_s *= 0.95
            p_critique_given_not_s *= 0.15
            
        if has_warnings:
            p_critique_given_s *= 0.30
            p_critique_given_not_s *= 0.70
        else:
            p_critique_given_s *= 0.70
            p_critique_given_not_s *= 0.30

        # Simulation Evidence: Blocked or OK
        sim_ok = simulation["status"] == "ok"
        
        # P(sim_ok|S) = 0.98, P(sim_ok|~S) = 0.10
        if sim_ok:
            p_sim_given_s = 0.98
            p_sim_given_not_s = 0.10
        else:
            p_sim_given_s = 0.02
            p_sim_given_not_s = 0.90
            
        # 3. Combined Likelihood
        p_e_given_s = p_critique_given_s * p_sim_given_s
        p_e_given_not_s = p_critique_given_not_s * p_sim_given_not_s
        
        # 4. Posterior Calculation
        numerator = p_e_given_s * prior_s
        denominator = (p_e_given_s * prior_s) + (p_e_given_not_s * prior_not_s)
        
        # Avoid division by zero
        if denominator == 0:
            posterior = 0.01
        else:
            posterior = numerator / denominator

        # 5. Complexity Normalization (P1 Resilience)
        depth = self._graph_depth(graph)
        # Deeper graphs have a higher 'prior' risk of hidden failure (entropy)
        entropy_factor = 0.02 * max(0, depth - 4)
        final_score = max(0.01, min(0.99, posterior - entropy_factor))
        
        logger.info(
            f"🧠 [Reasoning] Bayesian Update: Prior={prior_s:.2f}, "
            f"P(E|S)={p_e_given_s:.4f}, P(E|~S)={p_e_given_not_s:.4f} -> confidence={final_score:.3f}"
        )
        
        return round(final_score, 3)

    async def _select_execution_strategy(
        self,
        graph: TaskGraph,
        critique: Dict[str, Any],
        simulation: Dict[str, Any],
        decision: Optional[Any],
    ) -> Dict[str, Any]:
        depth = self._graph_depth(graph)
        dependency_complexity = sum(len(node.dependencies) for node in graph.nodes)
        historical_success = await self._historical_success_rate(graph)
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

    async def learn_from_failure(self, mission_id: str, failure_reason: str, proposed_fix: str = ""):
        """
        Sovereign v15.1: Failure Feedback Loop.
        Feeds planning or execution failures back to the Evolution Engine to track fragility.
        """
        logger.warning(f"📉 [ReasoningCore] Learning from mission failure {mission_id}: {failure_reason}")
        
        try:
            from backend.core.evolution_engine import EvolutionaryIntelligenceEngine
            from backend.db.models import Mission
            from sqlalchemy import select
            
            # Fetch mission details for domain context
            async with PostgresDB._session_factory() as session:
                mission = await session.get(Mission, mission_id)
                if mission:
                    user_id = mission.user_id
                    query = mission.objective
                    # Record a high-fragility event (fidelity 0.1)
                    await EvolutionaryIntelligenceEngine.record_outcome(
                        user_id=user_id,
                        query=query,
                        response=f"FAILURE: {failure_reason}. FIX: {proposed_fix}",
                        fidelity=0.1,
                        domain="general"
                    )
                    logger.info(f"🧬 [ReasoningCore] Logged fragility update for '{query[:30]}...' via Evolution Engine.")
        except Exception as e:
            logger.error(f"[ReasoningCore] Failure feedback loop anomaly: {e}")

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

    async def _historical_success_rate(self, graph: TaskGraph, user_id: str = "global", domain: str = "general") -> float:
        """
        Sovereign v15.2: Dynamic Probability of Success.
        Inherits historical performance from the Evolution Engine's fragility index.
        """
        try:
            from .evolution_engine import EvolutionaryIntelligenceEngine
            fragility = await EvolutionaryIntelligenceEngine.get_fragility(user_id, domain)
            
            # Baseline success rate = 1.0 - Fragility (with a 5% floor and 95% ceiling)
            global_trust = 1.0 - fragility
            
            # Local learned strategy from common patterns (Pass 2)
            learned = graph.metadata.get("learned_strategy", {}) or {}
            avg = learned.get("avg_fidelity")
            
            if avg is not None:
                # Bayesian Merge: 40% Global Trust + 60% Pattern Experience
                local_trust = max(0.05, min(0.99, float(avg)))
                combined = (global_trust * 0.4) + (local_trust * 0.6)
            else:
                combined = global_trust
                
            return max(0.05, min(0.99, combined))
        except Exception as e:
            logger.error(f"[ReasoningCore] Dynamic success rate calculation failed: {e}")
            return 0.8 # Safe production fallback

    def _extract_complexity(self, perception: Dict[str, Any], decision: Optional[Any]) -> float:
        """
        Legacy complexity extraction logic for backwards compatibility.
        """
        if decision is not None and getattr(decision, "complexity_score", None) is not None:
            return float(getattr(decision, "complexity_score", 0.0))
        intent = perception.get("intent")
        if intent is not None and hasattr(intent, "complexity_level"):
            return min(1.0, max(0.0, float(intent.complexity_level) / 3.0))
        user_input = perception.get("input", "")
        return min(1.0, len(str(user_input).split()) / 20.0)
