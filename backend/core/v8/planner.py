import logging
import json
import random
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

# V8.7 Evolution: Import Fragility for Swarm Triggering
from .learning import FragilityTracker
from ..orchestrator_types import ToolResult

logger = logging.getLogger(__name__)

class TaskNode(BaseModel):
    id: str
    agent: str
    description: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list) # IDs of parent tasks
    critical: bool = True
    retry_count: int = 2
    metadata: Dict[str, Any] = Field(default_factory=dict) # Swarm context, mood, etc.

class TaskGraph(BaseModel):
    nodes: List[TaskNode] = Field(default_factory=list)
    results: Dict[str, ToolResult] = Field(default_factory=dict)
    
    def add_node(self, node: TaskNode):
        self.nodes.append(node)
        
    def to_dict(self):
        return [n.dict() for n in self.nodes]

    def is_complete(self) -> bool:
        return len(self.results) == len(self.nodes)

    def get_ready_tasks(self) -> List[TaskNode]:
        completed_ids = set(self.results.keys())
        return [
            n for n in self.nodes 
            if n.id not in completed_ids and all(dep in completed_ids for dep in n.dependencies)
        ]

    def mark_complete(self, node_id: str, result: ToolResult):
        self.results[node_id] = result

    def validate_dag(self):
        """
        Sovereign v1.0.0-RC1: Topological Safety Audit.
        Ensures the mission graph is a Directed Acyclic Graph (DAG) using DFS.
        """
        adj = {n.id: n.dependencies for n in self.nodes}
        visited = set()
        path = set()

        def has_cycle(node_id):
            if node_id in path: return True
            if node_id in visited: return False
            
            visited.add(node_id)
            path.add(node_id)
            for dep in adj.get(node_id, []):
                if has_cycle(dep): return True
            path.remove(node_id)
            return False

        for node in self.nodes:
            if has_cycle(node.id):
                logger.error(f"[V9 Planner] Topological Violation: Cycle detected at {node.id}")
                raise ValueError(f"Neural Topology Error: Mission graph contains a cycle at {node.id}")
        
        logger.info("[V9 Planner] Topological Audit Successful. DAG is valid.")

class LlmDecomposer:
    """
    Sovereign v9.8: LLM-Driven Mission Decomposition.
    Deconstructs complex goals into a structured DAG of agent tasks.
    """
    @staticmethod
    async def decompose(goal_objective: str, user_input: str, perception: Dict[str, Any]) -> TaskGraph:
        from backend.utils.llm_utils import call_lightweight_llm
        
        prompt = f"""
You are the LEVI Sovereign Planner (v9.8). Your task is to decompose a complex cognitive mission into a Directed Acyclic Graph (DAG) of specialized agent tasks.

Mission Objective: {goal_objective}
User Input: {user_input}
Context: {json.dumps(perception.get('context', {{}}), indent=2)}

Available Agents:
- search_agent: Web search and retrieval.
- research_agent: Deep analysis of text/data.
- code_agent: Software engineering and architecture.
- python_repl_agent: Code execution and verification.
- document_agent: RAG-based document analysis.
- image_agent: Visual generation.
- video_agent: Motion synthesis.
- critic_agent: Qualitative review and feedback.
- consensus_agent: Reconciling multiple viewpoints.

Output ONLY a JSON object representing the TaskGraph:
{{
  "nodes": [
    {{
      "id": "task_id",
      "agent": "agent_name",
      "description": "Clear step description",
      "inputs": {{"key": "value"}},
      "dependencies": ["parent_task_id"],
      "critical": true
    }}
  ]
}}

Guidelines:
1. Parallelize when possible.
2. Use template placeholders like {{task_id.result}} for dependency resolution in inputs.
3. Keep the graph efficient.
"""
        try:
            response = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in response: response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())
            graph = TaskGraph()
            for node_data in data.get("nodes", []):
                graph.add_node(TaskNode(**node_data))
            
            graph.validate_dag() # v1.0.0-RC1 Safety
            return graph
        except Exception as e:
            logger.error(f"[LlmDecomposer] Neural decomposition drift: {e}")
            return None

class DAGPlanner:
    """
    LeviBrain v9.8: Dynamic & Swarm-Aware DAG Planner.
    Generates dynamic task graphs using rules for speed and LLM for complexity.
    """

    async def build_task_graph(self, goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        Strategic Task Graph Construction with Hybrid Logic (v9.8).
        """
        from .engine_registry import EngineRegistry
        
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        user_id = perception.get("user_id", "default_user")
        
        # 1. COMPLEXITY BRANCH: LLM-Driven Dynamic Planning (Level 4+)
        if complexity >= 4:
            logger.info("[V9 Planner] High Complexity Detected. Executing Dynamic LLM Decomposition...")
            dynamic_graph = await LlmDecomposer.decompose(goal.objective, user_input, perception)
            if dynamic_graph and dynamic_graph.nodes:
                return dynamic_graph
            logger.warning("[V9 Planner] Dynamic decomposition failed. Falling back to swarm templates.")

        graph = TaskGraph()
        
        # 2. ENGINE-AWARE SHORTCUT: Check if a Level 2 Engine can solve the whole mission
        engine_name = await EngineRegistry.get_engine_for_task(intent_type, intent.capabilities if intent else [])
        if engine_name and complexity < 3:
            logger.info(f"[V9 Planner] Engine Shortcut: Using {engine_name} for mission.")
            graph.add_node(TaskNode(
                id="t_engine_direct", 
                agent=engine_name, 
                description=f"Deterministic execution via specialized engine: {engine_name}",
                inputs={"input": user_input}
            ))
            return graph

        # 3. Fragility Check & Swarm Configuration
        fragility = FragilityTracker.get_fragility(user_id, intent_type)
        is_fragile = fragility > 0.6
        swarm_size = 5 if (is_fragile or complexity >= 3) else 3
        
        logger.info(f"[V9 Planner] Building DAG for {intent_type}. Fragility: {fragility:.2f}")

        # 4. Wave 0: Relational Discovery
        if complexity >= 3:
            graph.add_node(TaskNode(
                id="t_relation",
                agent="relation_agent",
                description="Explore Knowledge Graph Resonance",
                inputs={"objective": user_input, "user_id": user_id, "depth": 2}
            ))

        # 5. Core Reasoning Wave (Swarm or Single)
        reasoner_ids = []
        core_agent = engine_name if engine_name else (f"{intent_type}_agent" if intent_type in ["code", "search", "document"] else "chat_agent")

        if is_fragile or complexity >= 2:
            # Swarm Execution Pass
            for i in range(swarm_size):
                tid = f"t_swarm_{intent_type}_{i}"
                mood = "precise" if i < int(swarm_size * 0.7) else "creative"
                
                graph.add_node(TaskNode(
                    id=tid,
                    agent=core_agent,
                    description=f"Swarm Member {i} ({mood.capitalize()}): High-fidelity reasoning",
                    inputs={"input": user_input, "mood": mood, "swarm_pass": i},
                    metadata={"swarm_group": intent_type, "mood": mood}
                ))
                reasoner_ids.append(tid)
        else:
            tid = "t_core"
            graph.add_node(TaskNode(
                id=tid,
                agent=core_agent,
                description="Consolidated cognitive pass",
                inputs={"input": user_input},
                metadata={"mood": "balanced"}
            ))
            reasoner_ids.append(tid)

        # 6. Specialized Verification & Consensus
        if intent_type == "code":
            for r_id in reasoner_ids:
                graph.add_node(TaskNode(
                    id=f"v_{r_id}",
                    agent="python_repl_agent",
                    description=f"Syntax Verification for {r_id}",
                    inputs={"code": f"{{{{{r_id}.result}}}}"},
                    dependencies=[r_id],
                    critical=True
                ))

        if len(reasoner_ids) > 1:
            graph.add_node(TaskNode(
                id="t_consensus",
                agent="consensus_agent",
                description="Multi-agent logic reconciliation",
                inputs={"input": user_input, "agent_outputs": "{{dependency_results}}"},
                dependencies=reasoner_ids,
                critical=True
            ))
            final_node_id = "t_consensus"
        else:
            final_node_id = reasoner_ids[-1]

        if complexity >= 2:
            graph.add_node(TaskNode(
                id="t_reflect",
                agent="critic_agent",
                description="Post-execution qualitative reflection",
                inputs={"draft": f"{{{{{final_node_id}.result}}}}", "goal": goal.objective},
                dependencies=[final_node_id],
                critical=False
            ))
        
        graph.validate_dag() # v1.0.0-RC1 Safety
        return graph

    async def refine_plan(self, original_graph: TaskGraph, reflection: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        Applies an Evolutionary Correction Wave based on qualitative feedback.
        """
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        fragility = FragilityTracker.get_fragility(perception.get("user_id"), intent_type)
        
        new_graph = TaskGraph()
        new_graph.add_node(TaskNode(
            id="t_correction",
            agent="chat_agent",
            description="High-fidelity corrective refinement",
            inputs={
                "input": perception.get("input"),
                "issues": reflection.get("issues"),
                "fix": reflection.get("fix"),
                "original_context": "{{all_results}}",
                "rigor": "exhaustive" if fragility > 0.5 else "standard"
            }
        ))
        return new_graph
