import logging
import json
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TaskNode(BaseModel):
    id: str
    agent: str
    description: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list) # IDs of parent tasks
    critical: bool = True
    retry_count: int = 2

class TaskGraph(BaseModel):
    nodes: List[TaskNode] = Field(default_factory=list)
    
    def add_node(self, node: TaskNode):
        self.nodes.append(node)
        
    def to_dict(self):
        return [n.dict() for n in self.nodes]

class DAGPlanner:
    """
    LeviBrain v8: DAG-Based Planner
    Generates a task graph with explicit dependencies and parallelization potential.
    """

    async def build_task_graph(self, goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        LeviBrain v8: Strategic Task Graph Construction.
        Optimizes for Wave-based parallel execution.
        """
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        
        graph = TaskGraph()
        
        # 1. Base Layer: Synchronous Local Path
        if complexity == 0:
            graph.add_node(TaskNode(
                id="t_local", 
                agent="local_agent", 
                description="Synchronous low-latency response",
                inputs={"input": user_input}
            ))
            return graph

        # 2. Sequential / Parallel Reasoning Layer
        if intent_type == "search":
             # Wave 1: Discovery
             graph.add_node(TaskNode(
                 id="t_search",
                 agent="search_agent",
                 description=f"Multi-vector search for: {user_input}",
                 inputs={"query": user_input}
             ))
             
             # Wave 2: Synthesis
             graph.add_node(TaskNode(
                 id="t_synth",
                 agent="chat_agent",
                 description="Synthesize investigative findings",
                 inputs={"input": user_input, "context": "{{t_search.result}}"},
                 dependencies=["t_search"]
             ))
             
        elif intent_type == "document":
             # Wave 1: Retrieval
             graph.add_node(TaskNode(
                 id="t_doc",
                 agent="document_agent",
                 description="RAG retrieval from Sovereign archive",
                 inputs={"query": user_input}
             ))
             
             # Wave 2: Synthesis
             graph.add_node(TaskNode(
                 id="t_synth",
                 agent="chat_agent",
                 description="Synthesize document intelligence",
                 inputs={"input": user_input, "context": "{{t_doc.result}}"},
                 dependencies=["t_doc"]
             ))

        elif intent_type == "code":
             # Wave 1: Architecture & Implementation
             graph.add_node(TaskNode(
                 id="t_code",
                 agent="code_agent",
                 description="Architect and implement solution code",
                 inputs={"input": user_input}
             ))
             
             # Wave 2: Verification
             graph.add_node(TaskNode(
                 id="t_verify",
                 agent="python_repl_agent",
                 description="Verify code syntax and logic in sandbox",
                 inputs={"code": "{{t_code.result}}"},
                 dependencies=["t_code"]
             ))

        else: # Intent: Chat / Analytical
             graph.add_node(TaskNode(
                 id="t_core",
                 agent="chat_agent",
                 description="Primary cognitive reasoning pass",
                 inputs={"input": user_input}
             ))

        # 3. v8.5: Consensus Node Injection (Debate Wave)
        if complexity >= 3 and len(graph.nodes) > 1:
            reasoner_ids = [n.id for n in graph.nodes if n.id != "t_local"]
            graph.add_node(TaskNode(
                id="t_consensus",
                agent="consensus_agent",
                description="Swarm reconciliation and conflict resolution",
                inputs={
                    "input": user_input,
                    "agent_outputs": "{{all_results}}"
                },
                dependencies=reasoner_ids,
                critical=True
            ))

        # 4. Universal v8 Reflection Pass
        if complexity >= 2:
            last_node_id = graph.nodes[-1].id
            graph.add_node(TaskNode(
                id="t_reflect",
                agent="critic_agent",
                description="High-fidelity qualitative reflection pass",
                inputs={
                    "draft": f"{{{{{last_node_id}.result}}}}", 
                    "goal": goal.objective,
                    "criteria": goal.success_criteria
                },
                dependencies=[last_node_id],
                critical=False
            ))

        return graph

    async def refine_plan(self, original_graph: TaskGraph, reflection: Dict[str, Any], goal: Any, perception: Dict[str, Any]) -> TaskGraph:
        """
        Applies a 'Correction Wave' to the task graph based on reflection results.
        """
        logger.info("[V8 Planner] Refining plan based on reflection issues: %s", reflection.get("issues", []))
        
        new_graph = TaskGraph()
        
        # 1. Inherit successful nodes if appropriate (simplified for v8)
        # 2. Add Correction Node
        new_graph.add_node(TaskNode(
            id="t_correction",
            agent="chat_agent",
            description="Apply corrective refinement to mission output",
            inputs={
                "input": perception.get("input"),
                "issues": reflection.get("issues"),
                "fix": reflection.get("fix"),
                "original_context": "{{all_results}}" # High-fidelity resolver
            }
        ))
        
        return new_graph
