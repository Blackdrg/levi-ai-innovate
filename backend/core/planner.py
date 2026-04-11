"""
Sovereign Planning Engine v14.0.
Generates a task graph (DAG) for cognitive missions based on Brain Policy.
"""

import logging
import re
import copy
from typing import Dict, Any, Optional, List
from .orchestrator_types import (
    IntentResult, 
    BrainDecision, 
    BrainMode, 
    TaskExecutionContract, 
    FailurePolicy,
    MemoryPolicy,
    ExecutionPolicy,
    LLMPolicy,
    IntentGraph
)
from .task_graph import TaskGraph, TaskNode
from .intent_classifier import HybridIntentClassifier
from .learning_loop import LearningLoop
from .strategy_ledger import StrategyLedger
from backend.utils.llm_utils import call_lightweight_llm as _call_lightweight_llm
from backend.utils.shield import PII_PATTERNS
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

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

class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:6]}")
    objective: str
    success_criteria: List[str] = Field(default_factory=list)
    validators: List[Dict[str, Any]] = Field(default_factory=list) # Machine-verifiable rules
    metrics: Dict[str, Any] = Field(default_factory=dict) # Quantitative targets
    priority: str = "medium"
    state: str = "active"
    mode: Optional[str] = None

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)

class GoalEngine:
    """
    Folded into Planner.
    Transforms user intent and brain policy into a formal cognitive goal.
    """
    def formulate_objective(self, perception: Dict[str, Any], mode: BrainMode) -> str:
        input_text = perception.get("input", "")
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        
        prefix = f"[{mode.value}] "
        if mode == BrainMode.SECURE:
             return f"{prefix}Securely process restricted query: {input_text}"
        if intent_type == "search":
            return f"{prefix}Retrieve and distill latest data: {input_text}"
        elif intent_type == "document":
            return f"{prefix}Synthesize document insights: {input_text}"
        elif intent_type == "code":
            return f"{prefix}Architect and verify code solution: {input_text}"
        elif intent_type == "image":
            return f"{prefix}Render high-fidelity creative concept: {input_text}"
        return f"{prefix}Synthesize coherent response: {input_text}"

    def generate_criteria(self, intent_type: str, complexity: int, user_input: str, mode: BrainMode) -> tuple:
        criteria = ["Syntactic coherence", "Factual alignment"]
        validators = []
        metrics = {"min_confidence": 0.8}
        
        if mode == BrainMode.FAST:
            criteria.append("Latency < 1000ms")
            metrics["max_latency_ms"] = 1000
        elif mode == BrainMode.DEEP:
            criteria = ["Logical chain validation", "Comprehensive synthesis", "Cross-domain resonance"]
            metrics["min_confidence"] = 0.95
        elif mode == BrainMode.SECURE:
            criteria.append("PII isolation")
            validators.append({"type": "sandbox_check", "level": "high"})
        
        if intent_type == "search":
             criteria.append("Citations included")
             validators.append({"type": "regex", "pattern": r"\[\d+\]|https?://", "field": "response"})
             metrics["min_sources"] = 2
        elif intent_type == "code":
             criteria.append("Syntactical correctness")
             validators.append({"type": "python_check", "field": "code"})
             metrics["max_latency_ms"] = 5000
        return criteria, validators, metrics

class PolicyEngine:
    """
    Folded into Planner.
    Calculates execution policy based on intent and risk.
    """
    async def select_mode(
        self, 
        intent: IntentResult, 
        complexity: float, 
        risk_level: float, 
        user_id: str = "default",
        resonance_data: Optional[List[Dict[str, Any]]] = None
    ) -> BrainMode:
        if risk_level > 0.7: return BrainMode.SECURE
        
        # v14.1 Fragility Escalation
        intent_type = intent.intent_type if intent else "chat"
        from .evolution_engine import EvolutionaryIntelligenceEngine
        fragility = await EvolutionaryIntelligenceEngine.get_fragility(user_id, intent_type)
        
        if fragility > 0.4:
            logger.warning(f"[Policy] Escalating to DEEP mode due to high fragility ({fragility:.2f}) in domain: {intent_type}")
            return BrainMode.DEEP

        # v14.2 Knowledge-Based Escalation (Neo4j Resonance)
        if resonance_data:
            high_weight_atoms = [r for r in resonance_data if r.get("weight", 0) > 0.8]
            if len(high_weight_atoms) > 2:
                logger.info(f"[Policy] Escalating to DEEP mode due to high knowledge density ({len(high_weight_atoms)} high-weight atoms).")
                return BrainMode.DEEP

        if intent.intent_type == "search" or "research" in intent.intent_type: return BrainMode.RESEARCH
        if complexity > 0.8: return BrainMode.DEEP
        if complexity > 0.5: return BrainMode.BALANCED
        return BrainMode.FAST

    def allocate_agents(self, mode: BrainMode, intent: IntentResult, complexity: float) -> Dict[str, bool]:
        agents = {"planner": True, "critic": False, "retrieval": False, "browser": False, "docker": False}
        if mode == BrainMode.FAST: agents["planner"] = False
        if mode in [BrainMode.DEEP, BrainMode.RESEARCH, BrainMode.SECURE]: agents["critic"] = True
        if mode == BrainMode.RESEARCH or intent.intent_type == "search":
            agents["retrieval"] = True
            agents["browser"] = True
        if intent.intent_type == "code" and mode != BrainMode.FAST: agents["docker"] = True
        return agents

    def allocate_memory(self, mode: BrainMode, intent: IntentResult) -> MemoryPolicy:
        policy = MemoryPolicy(redis=True, postgres=True, neo4j=False, faiss=True)
        if mode in [BrainMode.RESEARCH, BrainMode.DEEP]: policy.neo4j = True
        if intent.intent_type == "knowledge": policy.neo4j = True
        return policy

    def define_execution_policy(self, mode: BrainMode, complexity: float) -> ExecutionPolicy:
        policy = ExecutionPolicy(parallel_waves=2, max_retries=1, sandbox_required=False)
        if complexity > 0.7: policy.parallel_waves = 4
        if complexity < 0.3: policy.parallel_waves = 1
        if mode == BrainMode.SECURE:
            policy.sandbox_required = True
            policy.max_retries = 0
        if mode == BrainMode.RESEARCH: policy.max_retries = 3
        return policy

    def define_llm_policy(self, mode: BrainMode, risk_level: float) -> LLMPolicy:
        # v14.1 Latency-Aware Depth Budgeting
        from .executor.guardrails import capture_resource_pressure
        pressure = capture_resource_pressure()
        max_depth = 5 # Production baseline
        if pressure.get("vram_pressure", 0) > 0.8:
            max_depth = 3
            logger.warning("[Policy] Resource pressure high: Capping DAG depth to 3.")
            
        policy = LLMPolicy(local_only=True, cloud_fallback=False)
        policy.max_dag_depth = max_depth
        if mode == BrainMode.DEEP and risk_level < 0.5: policy.cloud_fallback = True
        if mode == BrainMode.SECURE:
            policy.local_only = True
            policy.cloud_fallback = False
        return policy

# v14.1 Prebuilt Optimized Templates
HARD_TEMPLATES = {
    "search": [
        {"id": "t_search", "agent": "search_agent", "description": "Search pass", "critical": True},
        {"id": "t_synth", "agent": "chat_agent", "description": "Synthesis pass", "dependencies": ["t_search"]}
    ],
    "code": [
        {"id": "t_code", "agent": "code_agent", "description": "Code generation", "critical": True},
        {"id": "t_verify", "agent": "python_repl_agent", "description": "Sandbox verification", "dependencies": ["t_code"]}
    ],
    "research": [
        {"id": "t_search", "agent": "search_agent", "description": "Initial search", "critical": True},
        {"id": "t_browse", "agent": "browser_agent", "description": "Deep research", "dependencies": ["t_search"]},
        {"id": "t_synth", "agent": "chat_agent", "description": "Final report", "dependencies": ["t_browse"]}
    ]
}

class LlmDecomposer:
    """
    Sovereign v14.2.0: Neural Mission Deconstruction.
    Decomposes complex user goals into non-linear directed acyclic graphs.
    """
    @staticmethod
    async def decompose(objective: str, user_input: str, perception: Dict[str, Any]) -> Optional[TaskGraph]:
        # Sovereign v14.2: Neo4j Graph Resonance Integration
        context = perception.get("context", {})
        graph_resonance = context.get("long_term", {}).get("graph_resonance", [])
        
        resonance_text = ""
        if graph_resonance:
            resonance_text = "\nSovereign Knowledge Graph Resonance:\n" + "\n".join([
                f"- {r.get('entity', {}).get('text') or r.get('entity', {}).get('name')} (Type: {r.get('labels', [])})"
                for r in graph_resonance
            ])

        prompt = f"""
You are the LEVI Sovereign Planner (v14.2.0).
Decompose this mission into a Directed Acyclic Graph (DAG) of specialized agent tasks.

Mission Objective: {objective}
User Input: {user_input}
Context: {json.dumps(context, indent=2)}
{resonance_text}

Available Agents:
- search_agent, browser_agent, code_agent, python_repl_agent, document_agent, image_agent, video_agent, critic_agent, consensus_agent

Output ONLY a JSON object representing the TaskGraph:
{{
  "nodes": [
    {{
      "id": "task_id",
      "agent": "agent_name",
      "description": "Step description",
      "inputs": {{"key": "value"}},
      "dependencies": ["parent_id"],
      "critical": true
    }}
  ]
}}
"""
        try:
            from backend.utils.llm_utils import call_lightweight_llm
            response = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in response: response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())
            
            graph = TaskGraph()
            for node_data in data.get("nodes", []):
                graph.add_node(TaskNode(**node_data))
            
            return graph
        except Exception as e:
            logger.error(f"[LlmDecomposer] Decomposition failed: {e}")
            return None

class DAGPlanner:
    """
    LeviBrain v14.2.0: Hybrid DAG-Based Planner.
    Fuses hardcoded templates for speed with LLM decomposition for complexity.
    """
    def __init__(self):
        self.goal_engine = GoalEngine()
        self.policy_engine = PolicyEngine()

    async def generate_decision(self, user_input: str, perception: Dict[str, Any]) -> BrainDecision:
        intent = perception.get("intent")
        complexity = (intent.complexity_level / 3.0) if intent else 0.5
        risk_level = 0.8 if (intent and intent.is_sensitive) else 0.1
        
        user_id = perception.get("user_id", "default")
        resonance = perception.get("context", {}).get("long_term", {}).get("graph_resonance", [])
        
        mode = await self.policy_engine.select_mode(
            intent, 
            complexity, 
            risk_level, 
            user_id=user_id,
            resonance_data=resonance
        )
        enable_agents = self.policy_engine.allocate_agents(mode, intent, complexity)
        memory_policy = self.policy_engine.allocate_memory(mode, intent)
        execution_policy = self.policy_engine.define_execution_policy(mode, complexity)
        llm_policy = self.policy_engine.define_llm_policy(mode, risk_level)
        
        return BrainDecision(
            mode=mode,
            enable_agents=enable_agents,
            memory_policy=memory_policy,
            execution_policy=execution_policy,
            llm_policy=llm_policy,
            risk_level=risk_level,
            complexity_score=complexity
        )

    async def create_goal(self, perception: Dict[str, Any], decision: BrainDecision) -> Goal:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        mode = decision.mode
        
        objective = self.goal_engine.formulate_objective(perception, mode)
        success_criteria, validators, metrics = self.goal_engine.generate_criteria(intent_type, complexity, perception.get("input", ""), mode)
        priority = "high" if (complexity >= 3 or mode in [BrainMode.DEEP, BrainMode.SECURE]) else "medium"
        
        return Goal(
            objective=objective,
            success_criteria=success_criteria,
            validators=validators,
            metrics=metrics,
            priority=priority,
            mode=mode.value
        )


    async def build_task_graph(self, goal: Any, perception: Dict[str, Any], decision: Optional[BrainDecision] = None) -> TaskGraph:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        user_input = perception.get("input", "")
        mode = decision.mode if decision else BrainMode.BALANCED
        
        # 1. High Complexity / DEEP Mode: Dynamic LLM Decomposition
        if (intent and intent.complexity_level >= 3) or mode == BrainMode.DEEP:
            logger.info("[Planner] Elevating to Neural Decomposition...")
            graph = await LlmDecomposer.decompose(goal.objective, user_input, perception)
            if graph and graph.nodes:
                graph.validate_dag(max_depth=8)
                graph.metadata["cost_estimate"] = graph.estimate_cost()
                return graph

        # 2. Template Escalation
        if intent_type in HARD_TEMPLATES:
            logger.info(f"[Planner] Using hardcoded template for intent: {intent_type}")
            graph = self._build_from_static_template(HARD_TEMPLATES[intent_type], user_input, perception, decision)
            if graph:
                max_depth = decision.llm_policy.max_dag_depth if decision else 5
                graph.validate_dag(max_depth=max_depth)
                graph.metadata["cost_estimate"] = graph.estimate_cost()
                return graph

        # Default fallback creation logic (existing)...
        graph = TaskGraph()
        # ... (rest of simple logic) ...
        node_id = "t_core"
        graph.add_node(TaskNode(
            id=node_id,
            agent="chat_agent",
            description=f"Primary {mode.value} reasoning pass",
            inputs={"input": user_input},
            contract=self._generate_contract(node_id, "chat_agent")
        ))
        
        graph.metadata["cost_estimate"] = graph.estimate_cost()
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
