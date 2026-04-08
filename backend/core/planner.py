"""
Sovereign Planning Engine v14.0.
Generates a task graph (DAG) for cognitive missions based on Brain Policy.
"""

import logging
import re
import copy
from typing import Dict, Any, Optional, List
from .orchestrator_types import IntentResult, BrainDecision, BrainMode, TaskExecutionContract, FailurePolicy
from .task_graph import TaskGraph, TaskNode
from .intent_classifier import HybridIntentClassifier
from .learning_loop import LearningLoop
from backend.utils.llm_utils import call_lightweight_llm as _call_lightweight_llm
from backend.utils.shield import PII_PATTERNS

logger = logging.getLogger(__name__)

# Global Hybrid Intent Classifier
_INTENT_CLASSIFIER = HybridIntentClassifier()

async def detect_intent(user_input: str) -> IntentResult:
    """Unified intent detection for Perception Layer via Hybrid Classifier."""
    return await _INTENT_CLASSIFIER.classify(user_input)


async def call_lightweight_llm(messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
    """
    Compatibility bridge for legacy planner-adjacent modules that still import this helper here.
    """
    return await _call_lightweight_llm(messages, model=model)


def detect_sensitivity(text: str) -> bool:
    """
    Lightweight sensitivity detector used by learning and memory fallback logic.
    """
    if not text:
        return False
    lowered = text.lower()
    keyword_hits = [
        "password",
        "secret",
        "private key",
        "token",
        "ssn",
        "credit card",
        "bank account",
    ]
    if any(keyword in lowered for keyword in keyword_hits):
        return True
    return any(re.search(pattern, text) for pattern in PII_PATTERNS.values())

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
        learned_strategy = LearningLoop.get_best_strategy(intent_type)
        
        graph = TaskGraph()
        graph.metadata.update(
            {
                "intent_type": intent_type,
                "planner_mode": mode.value if hasattr(mode, "value") else str(mode),
                "learned_strategy": learned_strategy,
                "planning_passes": 1,
                "strict_schema": True,
                "retry_strategy": "exp_backoff_jitter",
            }
        )
        cached_graph = self._restore_cached_template(learned_strategy, user_input, perception)
        if cached_graph is not None:
            max_depth = decision.execution_policy.budget.max_dag_depth if decision else 8
            cached_graph.metadata.update(graph.metadata)
            cached_graph.metadata["template_cache_hit"] = True
            cached_graph.validate_dag(max_depth=max_depth)
            return cached_graph
        
        # 1. FAST MODE: Single node, no orchestration overhead
        if mode == BrainMode.FAST:
            node_id = "t_fast"
            agent = "local_agent" if intent_type == "chat" else "chat_agent"
            graph.add_node(TaskNode(
                id=node_id, 
                agent=agent, 
                description="Fast-path execution",
                inputs={"input": user_input},
                contract=self._generate_contract(node_id, agent, max_retries=1),
                fallback_output={"message": "Fast-path fallback response generated."},
                compensation_action=f"log_failure:{node_id}",
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
                 contract=self._generate_contract(node_id, "search_agent", max_retries=decision.execution_policy.max_retries if decision else 1),
                 fallback_output={"message": "Search unavailable, continue with partial context."},
                 compensation_action=f"log_failure:{node_id}",
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
                     contract=self._generate_contract(node_id, "browser_agent"),
                     fallback_output={"message": "Browser pass skipped."},
                     compensation_action=f"log_failure:{node_id}",
                 ))

             node_id = "t_synth"
             graph.add_node(TaskNode(
                 id=node_id,
                 agent="chat_agent",
                 description="Synthesize research results",
                 inputs={"input": user_input, "context": "{{t_search.result}}"},
                 dependencies=["t_search"] + (["t_browse"] if decision and decision.enable_agents.get("browser", False) else []),
                 contract=self._generate_contract(node_id, "chat_agent"),
                 fallback_output={"message": "Synthesis fallback used."},
                 compensation_action=f"log_failure:{node_id}",
             ))
             
        elif intent_type == "code":
             node_id = "t_code"
             graph.add_node(TaskNode(
                 id=node_id,
                 agent="code_agent",
                 description="Generate code solution",
                 inputs={"input": user_input},
                 contract=self._generate_contract(node_id, "code_agent"),
                 fallback_output={"message": "Code generation fallback used."},
                 compensation_action=f"log_failure:{node_id}",
             ))
             
             if decision and decision.enable_agents.get("docker", False):
                 node_id = "t_verify"
                 graph.add_node(TaskNode(
                     id=node_id,
                     agent="python_repl_agent",
                     description="Secure sandbox code verification",
                     inputs={"code": "{{t_code.result}}"},
                     dependencies=["t_code"],
                     contract=self._generate_contract(node_id, "python_repl_agent"),
                     fallback_output={"message": "Verification skipped; unverified output."},
                     compensation_action=f"log_failure:{node_id}",
                 ))

        else: # Default Cognitive Reasoning
             node_id = "t_core"
             graph.add_node(TaskNode(
                 id=node_id,
                 agent="chat_agent",
                 description=f"Primary {mode.value} reasoning pass",
                 inputs={"input": user_input, "mood": perception.get("context", {}).get("mood", "philosophical")},
                 contract=self._generate_contract(node_id, "chat_agent"),
                 fallback_output={"message": "Primary reasoning fallback used."},
                 compensation_action=f"log_failure:{node_id}",
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
                contract=self._generate_contract(node_id, "critic_agent"),
                fallback_output={"message": "Critique pass unavailable."},
                compensation_action=f"log_failure:{node_id}",
            ))

        # 4. Final Validation
        max_depth = decision.execution_policy.budget.max_dag_depth if decision else 8
        self.validate_graph(graph, max_depth=max_depth)
        graph.metadata["graph_template"] = self._serialize_template(graph)

        return graph

    def validate_graph(self, graph: Any, max_depth: int = 8):
        """Cycle detection and depth guard."""
        graph.validate_dag(max_depth=max_depth)

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
            contract=self._generate_contract(node_id, "chat_agent"),
            fallback_output={"message": "Refinement fallback used."},
            compensation_action=f"log_failure:{node_id}",
        ))
        task_graph.metadata["planning_passes"] = int(task_graph.metadata.get("planning_passes", 1)) + 1
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
            input_schema=self._default_input_schema(agent),
            output_schema=self._default_output_schema(),
            timeout_ms=kwargs.get("timeout_ms", timeout),
            max_retries=kwargs.get("max_retries", 2),
            strict_schema=kwargs.get("strict_schema", True),
            retry_strategy=kwargs.get("retry_strategy", "exp_backoff_jitter"),
            allowed_tools=kwargs.get("allowed_tools", [agent]),
            memory_scope=kwargs.get(
                "memory_scope",
                "task" if ("code" in agent or "repl" in agent or "search" in agent) else "session",
            ),
            failure_policy=kwargs.get("failure_policy", FailurePolicy(on_failure="retry"))
        )

    def _default_input_schema(self, agent: str) -> Dict[str, Any]:
        schema = {
            "input": {"type": "str", "required": False},
            "query": {"type": "str", "required": False},
            "context": {"type": "dict", "required": False},
            "draft": {"type": "str", "required": False},
            "goal": {"type": "str", "required": False},
            "issues": {"type": "list", "required": False},
            "strategy": {"type": "str", "required": False},
            "code": {"type": "str", "required": False},
            "mood": {"type": "str", "required": False},
        }
        if "search" in agent or "browser" in agent:
            schema["query"]["required"] = True
        elif "critic" in agent:
            schema["draft"]["required"] = True
        else:
            schema["input"]["required"] = True
        return schema

    def _default_output_schema(self) -> Dict[str, Any]:
        return {
            "success": {"type": "bool", "required": True},
            "data": {"type": "dict", "required": True},
            "message": {"type": "str", "required": True},
            "error": {"type": "optional[str]", "required": False},
            "agent": {"type": "str", "required": True},
            "latency_ms": {"type": "int", "required": True},
            "confidence": {"type": "float", "required": True},
            "fidelity_score": {"type": "float", "required": True},
            "cost_score": {"type": "int", "required": True},
            "total_tokens": {"type": "int", "required": True},
            "retryable": {"type": "bool", "required": True},
        }

    def _serialize_template(self, graph: TaskGraph) -> List[Dict[str, Any]]:
        template = []
        for node in graph.nodes:
            node_payload = node.model_dump(exclude={"result"})
            if node.contract is not None:
                node_payload["contract"] = node.contract.model_dump()
            template.append(node_payload)
        return template

    def _restore_cached_template(
        self,
        learned_strategy: Dict[str, Any],
        user_input: str,
        perception: Dict[str, Any],
    ) -> Optional[TaskGraph]:
        template = learned_strategy.get("graph_template")
        if not template:
            return None
        try:
            graph = TaskGraph()
            for raw_node in template:
                node_data = copy.deepcopy(raw_node)
                if "inputs" in node_data:
                    node_data["inputs"] = self._hydrate_template_inputs(node_data["inputs"], user_input, perception)
                graph.add_node(TaskNode(**node_data))
            graph.metadata["template_source"] = learned_strategy.get("graph_signature")
            return graph
        except Exception as exc:
            logger.warning("[Planner] Failed to restore cached DAG template: %s", exc)
            return None

    def _hydrate_template_inputs(
        self,
        inputs: Dict[str, Any],
        user_input: str,
        perception: Dict[str, Any],
    ) -> Dict[str, Any]:
        hydrated = copy.deepcopy(inputs)
        if "input" in hydrated:
            hydrated["input"] = user_input
        if "query" in hydrated:
            hydrated["query"] = user_input
        if "mood" in hydrated:
            hydrated["mood"] = perception.get("context", {}).get("mood", hydrated["mood"])
        return hydrated
