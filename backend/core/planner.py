"""
Sovereign Planning Engine v14.0.
Generates a task graph (DAG) for cognitive missions based on Brain Policy.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from .orchestrator_types import IntentResult, BrainDecision, BrainMode, TaskExecutionContract, FailurePolicy
from .task_graph import TaskGraph, TaskNode
from .intent_classifier import HybridIntentClassifier

logger = logging.getLogger(__name__)

# Global Hybrid Intent Classifier
_INTENT_CLASSIFIER = HybridIntentClassifier()

async def detect_intent(user_input: str) -> IntentResult:
    """Unified intent detection for Perception Layer via Hybrid Classifier."""
    return await _INTENT_CLASSIFIER.classify(user_input)

class DAGPlanner:
    """
    LeviBrain v14.0: DAG-Based Planner.
    Architecture: Follows DAG Shape Governance from Brain Policy.
    """

    async def build_task_graph(self, goal: Any, perception: Dict[str, Any], decision: Optional[BrainDecision] = None) -> TaskGraph:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        user_input = perception.get("input", "")
        mode = decision.mode if decision else BrainMode.BALANCED
        
        graph = TaskGraph()
        
        # 1. FAST MODE: Single node, no orchestration overhead
        if mode == BrainMode.FAST:
            node_id = "t_fast"
            agent = "local_agent" if intent_type == "chat" else "chat_agent"
            graph.add_node(TaskNode(
                id=node_id, 
                agent=agent, 
                description="Fast-path execution",
                inputs={"input": user_input},
                contract=self._generate_contract(node_id, agent, max_retries=1)
            ))
            return graph

        # 2. Pipeline Generation (Based on Intent & Policy)
        if intent_type == "search" or (decision and decision.enable_agents.get("retrieval", False)):
             node_id = "t_search"
             graph.add_node(TaskNode(
                 id=node_id,
                 agent="search_agent",
                 description=f"Retrieve latest data for: {user_input}",
                 inputs={"query": user_input},
                 retry_count=decision.execution_policy.max_retries if decision else 1,
                 contract=self._generate_contract(node_id, "search_agent", max_retries=decision.execution_policy.max_retries if decision else 1)
             ))
             
             if decision and decision.enable_agents.get("browser", False):
                 node_id = "t_browse"
                 graph.add_node(TaskNode(
                     id=node_id,
                     agent="browser_agent",
                     description="Deep web research pass",
                     inputs={"query": user_input},
                     dependencies=["t_search"],
                     critical=False,
                     contract=self._generate_contract(node_id, "browser_agent")
                 ))

             node_id = "t_synth"
             graph.add_node(TaskNode(
                 id=node_id,
                 agent="chat_agent",
                 description="Synthesize research results",
                 inputs={"input": user_input, "context": "{{t_search.result}}"},
                 dependencies=["t_search"] + (["t_browse"] if decision and decision.enable_agents.get("browser", False) else []),
                 contract=self._generate_contract(node_id, "chat_agent")
             ))
             
        elif intent_type == "code":
             node_id = "t_code"
             graph.add_node(TaskNode(
                 id=node_id,
                 agent="code_agent",
                 description="Generate code solution",
                 inputs={"input": user_input},
                 contract=self._generate_contract(node_id, "code_agent")
             ))
             
             if decision and decision.enable_agents.get("docker", False):
                 node_id = "t_verify"
                 graph.add_node(TaskNode(
                     id=node_id,
                     agent="python_repl_agent",
                     description="Secure sandbox code verification",
                     inputs={"code": "{{t_code.result}}"},
                     dependencies=["t_code"],
                     contract=self._generate_contract(node_id, "python_repl_agent")
                 ))

        else: # Default Cognitive Reasoning
             node_id = "t_core"
             graph.add_node(TaskNode(
                 id=node_id,
                 agent="chat_agent",
                 description=f"Primary {mode.value} reasoning pass",
                 inputs={"input": user_input, "mood": perception.get("context", {}).get("mood", "philosophical")},
                 contract=self._generate_contract(node_id, "chat_agent")
             ))

        # 3. CRITIC Activation (DAG Shape Governance)
        if decision and decision.enable_agents.get("critic", False):
            last_id = graph.nodes[-1].id
            node_id = "t_reflect"
            graph.add_node(TaskNode(
                id=node_id,
                agent="critic_agent",
                description="Qualitative reflection pass (v14.0 Policy)",
                inputs={"draft": f"{{{{{last_id}.result}}}}", "goal": goal.objective},
                dependencies=[last_id],
                critical=False,
                contract=self._generate_contract(node_id, "critic_agent")
            ))

        # 4. Final Validation
        max_depth = decision.execution_policy.budget.max_dag_depth if decision else 8
        self.validate_graph(graph, max_depth=max_depth)

        return graph

    def validate_graph(self, graph: Any, max_depth: int = 8):
        """Cycle detection and depth guard."""
        visited = set()
        path = set()
        nodes_map = {n.id: n for n in graph.nodes}

        def has_cycle(node_id):
            if node_id in path: return True
            if node_id in visited: return False
            visited.add(node_id)
            path.add(node_id)
            node = nodes_map.get(node_id)
            if node:
                for dep in node.dependencies:
                    if has_cycle(dep): return True
            path.remove(node_id)
            return False

        for node in graph.nodes:
            if has_cycle(node.id):
                raise ValueError(f"Self-referencing dependency in mission plan: {node.id}")
        
        def depth(node_id: str, memo: Dict[str, int]) -> int:
            if node_id in memo:
                return memo[node_id]
            node = nodes_map.get(node_id)
            if not node or not node.dependencies:
                memo[node_id] = 1
                return 1
            d = 1 + max(depth(dep, memo) for dep in node.dependencies)
            memo[node_id] = d
            return d
        
        depths = [depth(n.id, {}) for n in graph.nodes]
        if depths and max(depths) > max_depth:
            raise ValueError(f"DAG depth {max(depths)} exceeds limit {max_depth}")

    async def refine_plan(self, task_graph: TaskGraph, reflection: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """Plan Refinement (Following v14.0 Failure Policy)."""
        leaf_ids = [n.id for n in task_graph.nodes if not any(n.id in other.dependencies for other in task_graph.nodes)]
        node_id = f"t_refine_{len(task_graph.nodes)}"
        task_graph.add_node(TaskNode(
            id=node_id,
            agent="chat_agent",
            description="Cognitive refinement pass",
            inputs={"input": perception.get("input"), "issues": reflection.get("issues", []), "strategy": reflection.get("fix", "")},
            dependencies=leaf_ids,
            critical=True,
            contract=self._generate_contract(node_id, "chat_agent")
        ))
        return task_graph

    def _generate_contract(self, task_id: str, agent: str, **kwargs) -> TaskExecutionContract:
        """
        v14.0 TEC: Generates an explicit execution contract for a task node.
        """
        # Default heuristics for agent capabilities
        timeout = 30000
        if "search" in agent or "browser" in agent: timeout = 60000
        if "code" in agent or "repl" in agent: timeout = 45000
        
        return TaskExecutionContract(
            task_id=task_id,
            input_schema={}, # To be populated by Pydantic schema of the agent if available
            output_schema={},
            timeout_ms=kwargs.get("timeout_ms", timeout),
            max_retries=kwargs.get("max_retries", 2),
            allowed_tools=kwargs.get("allowed_tools", []),
            memory_scope=kwargs.get("memory_scope", "session"),
            failure_policy=kwargs.get("failure_policy", FailurePolicy(action="retry"))
        )
