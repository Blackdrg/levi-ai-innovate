import logging
import json
import random
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

# V8.7 Evolution: Import Fragility for Swarm Triggering
from .learning import FragilityTracker

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
    
    def add_node(self, node: TaskNode):
        self.nodes.append(node)
        
    def to_dict(self):
        return [n.dict() for n in self.nodes]

class DAGPlanner:
    """
    LeviBrain v8.7: Swarm-Aware DAG Planner
    Generates dynamic task graphs with fragile-triggered swarms and mood diversity.
    """

    async def build_task_graph(self, goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        Strategic Task Graph Construction with Engine-Aware Priorities (v8.12).
        """
        from .engine_registry import EngineRegistry
        
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        user_id = perception.get("user_id", "default_user")
        
        graph = TaskGraph()
        
        # 1. ENGINE-AWARE SHORTCUT: Check if a Level 2 Engine can solve the whole mission
        engine_name = await EngineRegistry.get_engine_for_task(intent_type, intent.capabilities if intent else [])
        if engine_name and complexity < 3:
            logger.info(f"[V8 Planner] Engine Shortcut: Using {engine_name} for mission.")
            graph.add_node(TaskNode(
                id="t_engine_direct", 
                agent=engine_name, 
                description=f"Deterministic execution via specialized engine: {engine_name}",
                inputs={"input": user_input}
            ))
            return graph

        # 2. Fragility Check & Swarm Configuration
        fragility = FragilityTracker.get_fragility(user_id, intent_type)
        is_fragile = fragility > 0.6
        swarm_size = 5 if (is_fragile or complexity >= 5) else 3
        
        logger.info(f"[V8 Planner] Building DAG for {intent_type}. Fragility: {fragility:.2f}")

        # 3. Wave 0: Relational Discovery (Engine-Aware)
        if complexity >= 4:
            graph.add_node(TaskNode(
                id="t_relation",
                agent="relation_agent",
                description="Explore Knowledge Graph Resonance",
                inputs={"objective": user_input, "user_id": user_id, "depth": 2}
            ))

        # 4. Core Reasoning Wave
        reasoner_ids = []
        
        # Determine core agent based on engine registry if possible
        core_agent = engine_name if engine_name else (f"{intent_type}_agent" if intent_type in ["code", "search", "document"] else "chat_agent")

        if is_fragile:
            # EXPLODE: Create a Swarm
            for i in range(swarm_size):
                tid = f"t_swarm_{intent_type}_{i}"
                mood = "precise" if i < int(swarm_size * 0.7) else "creative"
                
                graph.add_node(TaskNode(
                    id=tid,
                    agent=core_agent,
                    description=f"Swarm Member {i} ({mood.capitalize()}): Reasoning pass",
                    inputs={"input": user_input, "mood": mood, "swarm_pass": i},
                    metadata={"swarm_group": intent_type, "mood": mood}
                ))
                reasoner_ids.append(tid)
        else:
            # STANDARD: Single Core Node
            tid = "t_core"
            graph.add_node(TaskNode(
                id=tid,
                agent=core_agent,
                description="Standard cognitive reasoning pass",
                inputs={"input": user_input},
                metadata={"mood": "balanced"}
            ))
            reasoner_ids.append(tid)

        # 5. Specialized Verification (Deterministic)
        if intent_type == "code":
            for r_id in reasoner_ids:
                graph.add_node(TaskNode(
                    id=f"v_{r_id}",
                    agent="python_repl_agent",
                    description=f"Verify {r_id} execution",
                    inputs={"code": f"{{{{{r_id}.result}}}}"},
                    dependencies=[r_id],
                    critical=True
                ))

        # 6. Consensus & Reflection
        if is_fragile or (complexity >= 3 and len(graph.nodes) > 1):
            graph.add_node(TaskNode(
                id="t_consensus",
                agent="consensus_agent",
                description="Final reconciliation of swarm logic",
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
                description="Brain-level qualitative audit",
                inputs={"draft": f"{{{{{final_node_id}.result}}}}", "goal": goal.objective},
                dependencies=[final_node_id],
                critical=False
            ))

        return graph

        return graph

    async def refine_plan(self, original_graph: TaskGraph, reflection: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        Applies an Evolutionary Correction Wave.
        """
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        fragility = FragilityTracker.get_fragility(perception.get("user_id"), intent_type)
        
        new_graph = TaskGraph()
        new_graph.add_node(TaskNode(
            id="t_correction",
            agent="chat_agent",
            description="Apply corrective refinement with high-fidelity constraints",
            inputs={
                "input": perception.get("input"),
                "issues": reflection.get("issues"),
                "fix": reflection.get("fix"),
                "original_context": "{{all_results}}",
                "rigor": "exhaustive" if fragility > 0.5 else "standard"
            }
        ))
        return new_graph
