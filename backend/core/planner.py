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
from backend.services.cache_manager import CacheManager
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

    async def define_llm_policy(self, mode: BrainMode, risk_level: float, intent_type: str = "chat") -> LLMPolicy:
        # v14.1 Latency-Aware Depth Budgeting
        from .executor.guardrails import capture_resource_pressure
        pressure = capture_resource_pressure()
        max_depth = 5 # Production baseline
        if pressure.get("vram_pressure", 0) > 0.8:
            max_depth = 3
            logger.warning("[Policy] Resource pressure high: Capping DAG depth to 3.")
            
        # 📊 [Engine 9] Policy Gradient: Fetch Optimized Parameters
        from .policy_gradient import policy_gradient
        opt_params = await policy_gradient.get_optimal_params("planner", domain=intent_type)
            
        policy = LLMPolicy(
            local_only=True, 
            cloud_fallback=False,
            temperature=opt_params.get("temperature", 0.7),
            top_p=opt_params.get("top_p", 0.9),
            model=opt_params.get("model", "default"),
            max_tokens=opt_params.get("max_tokens", 1024)
        )
        policy.max_dag_depth = max_depth
        if mode == BrainMode.DEEP and risk_level < 0.5: policy.cloud_fallback = True
        if mode == BrainMode.SECURE:
            policy.local_only = True
            policy.cloud_fallback = False
        return policy

# v15.0 Prebuilt Optimized Templates (Tier 2 Speed Layer)
HARD_TEMPLATES = {
    "search": [
        {"id": "t_search", "agent": "SearchAgent", "description": "Global Web Pulse", "critical": True},
        {"id": "t_synth", "agent": "ChatAgent", "description": "Cognitive Synthesis", "dependencies": ["t_search"]}
    ],
    "code": [
        {"id": "t_code", "agent": "Artisan", "description": "Computational Logic", "critical": True},
        {"id": "t_verify", "agent": "Critic", "description": "Logic Verification", "dependencies": ["t_code"]}
    ],
    "research": [
        {"id": "t_arch", "agent": "ResearchArchitect", "description": "Recursive Discovery", "critical": True},
        {"id": "t_browse", "agent": "SearchAgent", "description": "Deep Retrieval", "dependencies": ["t_arch"]},
        {"id": "t_synth", "agent": "Analyst", "description": "Thematic Synthesis", "dependencies": ["t_browse"]}
    ],
    "image": [
        {"id": "t_image", "agent": "ImageArchitect", "description": "Visual Synthesis", "critical": True}
    ],
    "video": [
        {"id": "t_video", "agent": "VideoArchitect", "description": "Temporal Rendering", "critical": True}
    ],
    "document": [
        {"id": "t_lib", "agent": "Librarian", "description": "Semantic RAG", "critical": True},
        {"id": "t_analyst", "agent": "Analyst", "description": "Document Synthesis", "dependencies": ["t_lib"]}
    ],
    "knowledge": [
        {"id": "t_mem", "agent": "MemoryAgent", "description": "Fact Crystallization", "critical": True},
        {"id": "t_search", "agent": "SearchAgent", "description": "Global Context", "dependencies": ["t_mem"]}
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
        
        # 🧠 Phase 3: Context Injection Layer (Semantic + Episodic)
        semantic_traits = context.get("traits", [])
        semantic_prefs = context.get("preferences", {})
        episodic = context.get("mid_term", [])
        
        semantic_text = ""
        if semantic_traits or semantic_prefs:
            semantic_text = "\nSovereign Semantic Memory (Traits & Preferences):\n"
            for t in semantic_traits: 
                semantic_text += f"- {t}\n"
            if isinstance(semantic_prefs, dict):
                for k, v in semantic_prefs.items():
                    if k not in ["user_id", "id"] and v:
                        semantic_text += f"- {k}: {v}\n"
            elif isinstance(semantic_prefs, list):
                for p in semantic_prefs: semantic_text += f"- {p}\n"
                
        episodic_text = ""
        if episodic:
            episodic_text = "\nSovereign Episodic Memory (Recent Missions):\n"
            for m in episodic:
                episodic_text += f"- [{m.get('status', 'unknown')}] {m.get('objective', 'Unknown mission')}\n"

        resonance_text = ""
        if graph_resonance:
            resonance_text = "\nSovereign Knowledge Graph Resonance:\n" + "\n".join([
                f"- {r.get('entity', {}).get('text') or r.get('entity', {}).get('name')} (Type: {r.get('labels', [])})"
                for r in graph_resonance
            ])

        from backend.core.identity import identity_system
        bias = await identity_system.get_personality_bias_prompt()
        
        prompt = f"""
{bias}

You are the LEVI Sovereign Planner (Phase 3 Context-Aware).
Decompose this mission into a Directed Acyclic Graph (DAG) of specialized agent tasks.

Mission Objective: {objective}
User Input: {user_input}
{semantic_text}{episodic_text}{resonance_text}

### SCHEDULING HEURISTIC (Section 83.1)
Apply the Critical-Path Heuristic for task prioritization:
Priority = Complexity + Σ Latency(Children).
Tasks with the highest weight must be executed in early waves to minimize total mission latency.

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
        llm_policy = await self.policy_engine.define_llm_policy(mode, risk_level, intent_type=intent.intent_type if intent else "chat")
        
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
        graph = None
        
        # 🟢 Tier 3: Strategy Cache (DAG Reuse)
        cached_strat = await CacheManager.get_strategy(intent_type, user_input)
        if cached_strat:
            logger.info(f"🎯 [Planner] T3 STRATEGY HIT for {intent_type}")
            graph = self._restore_cached_template(cached_strat, user_input, perception)
            if graph: return graph
        

        # --- Step 2.4: Graduated Rule Override (REAL EVOLUTION) ---
        rule_override = await LearningLoop.check_rules(user_input)
        if rule_override:
            logger.info(f"🎯 [RuleEngine] Applying graduated override for '{user_input[:30]}...'")
            agents = rule_override.get("agent_sequence", [])
            template = []
            prev_id = None
            for i, agent in enumerate(agents):
                tid = f"rule_task_{i}"
                node = {"id": tid, "agent": agent, "description": f"Rule-based execution ({agent})", "critical": True}
                if prev_id:
                    node["dependencies"] = [prev_id]
                template.append(node)
                prev_id = tid
            
            graph = self._build_from_static_template(template, user_input, perception, decision)
            if graph:
                graph.metadata["origin"] = "graduated_rule"

        # 1. High Complexity / DEEP Mode: Dynamic LLM Decomposition
        if not graph and ((intent and intent.complexity_level >= 3) or mode == BrainMode.DEEP):
            logger.info("[Planner] Elevating to Neural Decomposition...")
            graph = await LlmDecomposer.decompose(goal.objective, user_input, perception)

        # 2. Template Escalation
        if not graph and (intent_type in HARD_TEMPLATES):
            logger.info(f"[Planner] Using hardcoded template for intent: {intent_type}")
            graph = self._build_from_static_template(HARD_TEMPLATES[intent_type], user_input, perception, decision)

        # 3. Default Fallback
        if not graph or not graph.nodes:
            logger.warning("[Planner] Fallback: Creating single-node DAG.")
            graph = TaskGraph()
            node_id = "t_core"
            graph.add_node(TaskNode(
                id=node_id,
                agent="chat_agent",
                description=f"Primary {mode.value} reasoning pass",
                inputs={"input": user_input},
                contract=self._generate_contract(node_id, "chat_agent")
            ))

        # 4. Final Structural Audit Pass (Hardened v15.0)
        self._structural_audit_pass(graph)
        
        # 🎓 Tier 3 Promotion: Store high-fidelity strategies
        if graph and graph.metadata.get("origin") != "template":
            await CacheManager.set_strategy(intent_type, user_input, self._serialize_template(graph))

        graph.metadata["cost_estimate"] = graph.estimate_cost()
        return graph

    def _structural_audit_pass(self, graph: TaskGraph):
        """
        Sovereign v15.0: Structural Audit Pass.
        Ensures DAG integrity, agent validity, and resource safety.
        """
        if not graph.nodes:
            logger.warning("[Planner-Audit] EMPTY graph detected.")
            return

        # 1. Cycle Detection (Already in validate_dag but reinforced)
        try:
            graph.validate_dag(max_depth=12)
        except Exception as e:
            logger.error(f"❌ [Planner-Audit] DAG Cycle Detected: {e}")
            raise ValueError(f"Invalid Graph Topology: {e}")

        # 2. Agent Validation (14-Agent Swarm Check)
        VALID_AGENTS = {
            "search_agent", "browser_agent", "code_agent", "python_repl_agent", 
            "document_agent", "image_agent", "video_agent", "critic_agent", 
            "consensus_agent", "scout", "artisan", "librarian", "analyst", "chat_agent"
        }
        for node in graph.nodes:
            if node.agent not in VALID_AGENTS:
                logger.warning(f"⚠️ [Planner-Audit] Unknown agent '{node.agent}' in node {node.id}. Mapping to chat_agent fallback.")
                node.agent = "chat_agent"

        # 3. Connection Audit (Orphan Detection)
        if len(graph.nodes) > 1:
            all_ids = {n.id for n in graph.nodes}
            all_deps = set()
            for n in graph.nodes:
                all_deps.update(n.dependencies)
            
            # Nodes with no dependencies (Roots)
            roots = [n.id for n in graph.nodes if not n.dependencies]
            # Nodes that aren't dependencies (Leaves)
            leaves = [n.id for n in graph.nodes if n.id not in all_deps]
            
            if not roots:
                logger.error("❌ [Planner-Audit] Graph has NO entry point!")
                raise ValueError("Graph has no root nodes.")
            if not leaves:
                logger.error("❌ [Planner-Audit] Graph has NO exit point (All nodes are dependencies)!")
                raise ValueError("Graph has no terminal nodes.")

        logger.info(f"✅ [Planner-Audit] Graph '{graph.metadata.get('origin', 'dynamic')}' verified: {len(graph.nodes)} nodes.")

    def _build_from_static_template(self, template: List[Dict[str, Any]], user_input: str, perception: Dict[str, Any], decision: Optional[BrainDecision]) -> TaskGraph:
        """
        Sovereign v15.0: Hydrates a static task template into a runnable TaskGraph.
        """
        graph = TaskGraph()
        for node_data in template:
            # Deep copy to avoid mutating the master template
            data = copy.deepcopy(node_data)
            tid = data["id"]
            agent = data["agent"]
            
            # Resolve inputs for the node
            inputs = data.get("inputs", {})
            if "query" in inputs or agent.lower() in ["searchagent", "scout", "librarian"]:
                inputs["query"] = user_input
            if "input" in inputs or not inputs:
                inputs["input"] = user_input
            
            # Generate Contract (TEC)
            contract = self._generate_contract(tid, agent)
            
            graph.add_node(TaskNode(
                id=tid,
                agent=agent,
                description=data.get("description", "Node execution"),
                inputs=inputs,
                dependencies=data.get("dependencies", []),
                critical=data.get("critical", False),
                contract=contract
            ))
        return graph

    def validate_graph(self, graph: Any, max_depth: int = 8):
        """Cycle detection and depth guard."""
        graph.validate_dag(max_depth=max_depth)

    async def refine_plan(self, task_graph: TaskGraph, reflection: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        Sovereign v15.0: Neural Re-planning (Self-Healing).
        Analyzes plan deficiencies and synthesizes a recovery sub-graph.
        """
        issues = reflection.get("issues", [])
        strategy = reflection.get("fix", "No specific strategy provided.")
        
        logger.warning(f"🔧 [Planner] Initiating Neural Re-planning for mission. Issues: {len(issues)}")
        
        # Determine if we need a deep recovery or just a refinement node
        if reflection.get("severity") == "high" or len(issues) > 1:
            logger.info("🧠 [Planner] Synthesis pass for recovery sub-graph...")
            
            # Use Decomposer to build a recovery branch
            recovery_prompt = f"RECOVERY MISSION: The following issues were found in the current plan: {issues}. Strategy: {strategy}"
            recovery_graph = await LlmDecomposer.decompose(recovery_prompt, perception.get("input", ""), perception)
            
            if recovery_graph and recovery_graph.nodes:
                # 1. Identify leaf nodes of current (failed) graph to link to
                leaf_ids = [n.id for n in task_graph.nodes if not any(n.id in other.dependencies for other in task_graph.nodes)]
                
                # 2. Merge recovery nodes into task_graph
                # We prefix recovery IDs to avoid collision
                for node in recovery_graph.nodes:
                    original_id = node.id
                    node.id = f"recovery_{node.id}"
                    # Link recovery roots to current leaves
                    if not node.dependencies:
                        node.dependencies = leaf_ids
                    else:
                        node.dependencies = [f"recovery_{d}" for d in node.dependencies]
                    
                    task_graph.add_node(node)
                
                logger.info(f"✅ [Planner] Merged {len(recovery_graph.nodes)} recovery nodes into mission graph.")
                return task_graph

        # Fallback: Default Refinement Node
        leaf_ids = [n.id for n in task_graph.nodes if not any(n.id in other.dependencies for other in task_graph.nodes)]
        node_id = f"t_refine_{len(task_graph.nodes)}"
        task_graph.add_node(TaskNode(
            id=node_id,
            agent="chat_agent",
            description="Cognitive refinement pass (Recovery)",
            inputs={"input": perception.get("input"), "issues": issues, "strategy": strategy},
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
