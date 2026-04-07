"""
Sovereign Planning Engine v14.0.
Generates a task graph (DAG) for cognitive missions based on Brain Policy.
"""

import logging
import re
from typing import Dict, Any, Optional
from .orchestrator_types import IntentResult, BrainDecision, BrainMode
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
            graph.add_node(TaskNode(
                id="t_fast", 
                agent="local_agent" if intent_type == "chat" else "chat_agent", 
                description="Fast-path execution",
                inputs={"input": user_input}
            ))
            return graph

        # 2. Pipeline Generation (Based on Intent & Policy)
        if intent_type == "search" or (decision and decision.enable_agents.get("retrieval", False)):
             graph.add_node(TaskNode(
                 id="t_search",
                 agent="search_agent",
                 description=f"Retrieve latest data for: {user_input}",
                 inputs={"query": user_input},
                 retry_count=decision.execution_policy.max_retries if decision else 1
             ))
             
             if decision and decision.enable_agents.get("browser", False):
                 graph.add_node(TaskNode(
                     id="t_browse",
                     agent="browser_agent",
                     description="Deep web research pass",
                     inputs={"query": user_input},
                     dependencies=["t_search"],
                     critical=False
                 ))

             graph.add_node(TaskNode(
                 id="t_synth",
                 agent="chat_agent",
                 description="Synthesize research results",
                 inputs={"input": user_input, "context": "{{t_search.result}}"},
                 dependencies=["t_search"] + (["t_browse"] if decision and decision.enable_agents.get("browser", False) else [])
             ))
             
        elif intent_type == "code":
             graph.add_node(TaskNode(
                 id="t_code",
                 agent="code_agent",
                 description="Generate code solution",
                 inputs={"input": user_input}
             ))
             
             if decision and decision.enable_agents.get("docker", False):
                 graph.add_node(TaskNode(
                     id="t_verify",
                     agent="python_repl_agent",
                     description="Secure sandbox code verification",
                     inputs={"code": "{{t_code.result}}"},
                     dependencies=["t_code"]
                 ))

        else: # Default Cognitive Reasoning
             graph.add_node(TaskNode(
                 id="t_core",
                 agent="chat_agent",
                 description=f"Primary {mode.value} reasoning pass",
                 inputs={"input": user_input, "mood": perception.get("context", {}).get("mood", "philosophical")}
             ))

        # 3. CRITIC Activation (DAG Shape Governance)
        if decision and decision.enable_agents.get("critic", False):
            last_id = graph.nodes[-1].id
            graph.add_node(TaskNode(
                id="t_reflect",
                agent="critic_agent",
                description="Qualitative reflection pass (v14.0 Policy)",
                inputs={"draft": f"{{{{{last_id}.result}}}}", "goal": goal.objective},
                dependencies=[last_id],
                critical=False
            ))

        # 4. Final Validation
        self.validate_graph(graph)

        return graph

    def validate_graph(self, graph: Any):
        """Standard Cycle Detection."""
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

    async def refine_plan(self, task_graph: TaskGraph, reflection: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """Plan Refinement (Following v14.0 Failure Policy)."""
        leaf_ids = [n.id for n in task_graph.nodes if not any(n.id in other.dependencies for other in task_graph.nodes)]
        task_graph.add_node(TaskNode(
            id=f"t_refine_{len(task_graph.nodes)}",
            agent="chat_agent",
            description="Cognitive refinement pass",
            inputs={"input": perception.get("input"), "issues": reflection.get("issues", []), "strategy": reflection.get("fix", "")},
            dependencies=leaf_ids,
            critical=True
        ))
        return task_graph
