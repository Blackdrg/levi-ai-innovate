import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Union

from sqlalchemy import case, func, select

from backend.core.task_graph import TaskGraph
from backend.db.models import CognitiveUsage, Mission
from backend.db.neo4j_connector import Neo4jStore
from backend.db.postgres import PostgresDB

logger = logging.getLogger(__name__)


@dataclass
class SimulationState:
    mission_id: str
    nodes_executed: int
    nodes_total: int
    failures: int
    estimated_latency_ms: float
    estimated_success_prob: float


class WorldModel:
    """
    Statistical Simulation Engine (v16.2.0 - PROTOTYPE).
    Provides predictive planning using Monte Carlo simulations and heuristic grounding.
    This component acts as a 'statistical label' for mission outcomes, 
    not a formal causal physical world model.
    """

    def __init__(self):
        self.tree: Dict[str, Any] = {}
        self.graph_db = Neo4jStore()

    async def ground_plan(self, goal_objective: str, task_graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        [V16.2.0-GA] Hardened Grounding Pass.
        Uses LLM-as-Critic to identify world-model violations and safety risks.
        """
        from backend.utils.llm_utils import call_heavyweight_llm
        import json

        prompt = (
            "You are the LEVI-AI World Model Sage. Evaluate the following mission objective for safety, "
            "ethical alignment, and system-level risk.\n\n"
            "### MISSION OBJECTIVE\n"
            f"{goal_objective}\n\n"
            "### TASK DATA\n"
            f"{json.dumps(task_graph_data, indent=2)}\n\n"
            "### OUTPUT FORMAT (JSON ONLY)\n"
            "{\n"
            "  \"is_valid\": true,\n"
            "  \"issues\": [],\n"
            "  \"grounding_status\": \"neo4j_verified\",\n"
            "  \"simulation_resonance\": 0.95\n"
            "}"
        )

        try:
            raw_res = await call_heavyweight_llm([{"role": "user", "content": prompt}], temperature=0.1)
            import re
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                audit = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in World Model grounding response")

            # Still mix in Neo4j resonance if entities are present (Hybrid)
            entities = [token for token in goal_objective.split() if token[:1].isupper()][:5]
            if entities:
                resonance_tasks = [self.graph_db.get_resonance(entity, tenant_id="global") for entity in entities]
                resonance = await asyncio.gather(*resonance_tasks)
                for entity, hits in zip(entities, resonance):
                    for hit in hits:
                        name = str(hit.get("name", "")).upper()
                        if "BLOCK" in name or "DENY" in name:
                            audit["issues"].append(f"Constraint violation around entity '{entity}' (Neo4j).")
                            audit["is_valid"] = False
                            break

            return audit

        except Exception as e:
            logger.error(f"[WorldModel] LLM Grounding failed: {e}. Falling back to emergency rules.")
            # Emergency Rule Fallback
            issues = []
            if any(token in goal_objective.lower() for token in ["delete prod", "drop production", "exfiltrate"]):
                issues.append("Emergency safety rule: Destructive prod ops blocked.")
            return {
                "is_valid": not issues,
                "issues": issues,
                "grounding_status": "emergency_fallback",
                "simulation_resonance": 0.5
            }

    async def simulate_plan(self, plan_dag: Union[TaskGraph, Dict[str, Any]], iterations: int = 100) -> Dict[str, Any]:
        nodes = self._normalize_nodes(plan_dag)
        if not nodes:
            return {
                "successes": 0,
                "failures": 1,
                "failure_modes": {"empty_plan": 1},
                "avg_latency_ms": 0.0,
                "success_probability": 0.0,
                "failure_probability": 1.0,
            }

        outcomes = {"successes": 0, "failures": 0, "failure_modes": {}, "avg_latency_ms": 0.0}
        latencies: List[float] = []
        for _ in range(iterations):
            result = await self._simulate_single_execution(nodes)
            if result["success"]:
                outcomes["successes"] += 1
            else:
                outcomes["failures"] += 1
                failure_mode = result.get("failure_reason", "unknown")
                outcomes["failure_modes"][failure_mode] = outcomes["failure_modes"].get(failure_mode, 0) + 1
            latencies.append(result["latency_ms"])

        total = max(1, iterations)
        outcomes["success_probability"] = outcomes["successes"] / total
        outcomes["avg_latency_ms"] = sum(latencies) / len(latencies) if latencies else 0.0
        outcomes["failure_probability"] = outcomes["failures"] / total
        return outcomes

    async def simulate_mission(self, objective: str, plan_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        simulation = await self.simulate_plan({"nodes": plan_nodes}, iterations=50)
        return {
            "status": "simulated" if simulation["success_probability"] >= 0.75 else "blocked_risk",
            "fidelity_prediction": simulation["success_probability"],
            "risk_assessment": "low" if simulation["success_probability"] >= 0.85 else "med" if simulation["success_probability"] >= 0.65 else "high",
            "causal_link_verified": simulation["success_probability"] >= 0.75,
            "bottlenecks": list(simulation["failure_modes"].keys()),
            "failure_modes": simulation["failure_modes"],
            "avg_latency_ms": simulation["avg_latency_ms"],
        }

    async def simulate_counterfactual(self, objective: str, plan_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        base = await self.simulate_plan({"nodes": plan_nodes}, iterations=30)
        reduced = plan_nodes[:-1] if len(plan_nodes) > 1 else plan_nodes
        counter = await self.simulate_plan({"nodes": reduced}, iterations=30)
        return {
            "status": "counterfactual_complete",
            "risk_assessment": "high" if base["success_probability"] < 0.75 else "low",
            "counterfactuals": [
                {
                    "source_node": plan_nodes[-1].get("id") if plan_nodes else "none",
                    "base_success_probability": base["success_probability"],
                    "counterfactual_success_probability": counter["success_probability"],
                }
            ],
        }

    async def simulate_outcome(self, action: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "projected_state": dict(current_state),
            "confidence": 0.9 if "safe" in action.lower() else 0.7,
        }

    async def _simulate_single_execution(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_latency = 0.0
        for node in nodes:
            task_result = await self._simulate_task(node)
            total_latency += task_result["latency_ms"]
            if not task_result["success"]:
                return {
                    "success": False,
                    "failure_reason": task_result.get("reason", "unknown"),
                    "latency_ms": max(0.0, total_latency),
                }
        return {"success": True, "latency_ms": max(0.0, total_latency)}

    async def _simulate_task(self, node: Dict[str, Any]) -> Dict[str, Any]:
        agent_id = str(node.get("agent") or "unknown")
        historical = await self._get_historical_performance(agent_id)

        if not historical:
            success_rate = 0.85
            avg_latency = 1500.0
            std_latency = 400.0
        else:
            success_rate = historical["success_rate"]
            avg_latency = historical["avg_latency_ms"]
            std_latency = historical["std_latency_ms"]

        latency = max(50.0, random.gauss(avg_latency, max(50.0, std_latency)))
        success = random.random() < success_rate
        if success:
            return {"success": True, "latency_ms": latency}
        return {
            "success": False,
            "reason": f"Agent {agent_id} failure (simulated)",
            "latency_ms": latency,
        }

    async def _get_historical_performance(self, agent_id: str) -> Dict[str, float]:
        try:
            async with PostgresDB.session_scope() as session:
                success_case = case((Mission.status.in_(["success", "completed", "COMPLETE"]), 1.0), else_=0.0)
                stmt = (
                    select(
                        func.avg(success_case).label("success_rate"),
                        func.avg(CognitiveUsage.latency_ms).label("avg_latency_ms"),
                        func.coalesce(func.stddev_pop(CognitiveUsage.latency_ms), 250.0).label("std_latency_ms"),
                    )
                    .select_from(CognitiveUsage)
                    .join(Mission, Mission.mission_id == CognitiveUsage.mission_id, isouter=True)
                    .where(CognitiveUsage.agent == agent_id)
                )
                row = (await session.execute(stmt)).mappings().first()
                if not row or row["avg_latency_ms"] is None:
                    return {
                        "success_rate": 0.90,
                        "avg_latency_ms": 1500.0,
                        "std_latency_ms": 500.0,
                    }
                return {
                    "success_rate": float(row["success_rate"] or 0.90),
                    "avg_latency_ms": float(row["avg_latency_ms"] or 1500.0),
                    "std_latency_ms": max(50.0, float(row["std_latency_ms"] or 500.0)),
                }
        except Exception as exc:
            logger.warning("[WorldModel] Historical performance lookup degraded for %s: %s", agent_id, exc)
            return {
                "success_rate": 0.90,
                "avg_latency_ms": 1500.0,
                "std_latency_ms": 500.0,
            }

    def _normalize_nodes(self, plan_dag: Union[TaskGraph, Dict[str, Any]]) -> List[Dict[str, Any]]:
        if isinstance(plan_dag, TaskGraph):
            ordered = []
            for wave in plan_dag.get_execution_waves():
                ordered.extend(
                    {
                        "id": node.id,
                        "agent": node.agent,
                        "description": node.description,
                        "dependencies": list(node.dependencies),
                    }
                    for node in wave
                )
            return ordered
        if isinstance(plan_dag, dict):
            nodes = plan_dag.get("nodes", [])
            return [node.model_dump() if hasattr(node, "model_dump") else dict(node) for node in nodes]
        return []

    # -------------------------------------------------------------------------
    # CAUSAL CONSISTENCY (Stage 8)
    # -------------------------------------------------------------------------

    async def verify_causality(self, response: str, intent: Any) -> Dict[str, Any]:
        """
        [v16.3.0] Verifies that the response doesn't violate causal constraints.
        Stored in the Neo4j knowledge graph as Constraint nodes.
        """
        logger.info("[WorldModel] Verifying causal consistency for response...")
        
        # 1. Entity Extraction (Simple)
        entities = [word.strip(",.?!\"") for word in response.split() if word and word[0].isupper() and len(word) > 2]
        
        anomalies = []
        for entity in set(entities):
            try:
                # Check for conflict triplets in Neo4j
                conflicts = await self.graph_db.get_resonance(entity, tenant_id="global")
                for c in conflicts:
                    if c.get("type") == "CONSTRAINT" and c.get("effect") == "BLOCK":
                        condition = c.get("condition", "").lower()
                        if condition and condition in response.lower():
                            anomalies.append(f"Causal Violation: Entity '{entity}' has a BLOCK constraint for '{condition}'.")
            except Exception as e:
                logger.warning(f"[WorldModel] Neo4j resonance failed for {entity}: {e}")

        return {
            "is_logical": len(anomalies) == 0,
            "anomalies": anomalies,
            "resonance_score": 1.0 if not anomalies else 0.4
        }

