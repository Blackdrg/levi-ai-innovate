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
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        
        graph = TaskGraph()
        
        # 1. Base Layer (Direct Local / Fast Path)
        if complexity == 0:
            graph.add_node(TaskNode(
                id="t_local", 
                agent="local_agent", 
                description="Fast path synchronous response",
                inputs={"input": user_input}
            ))
            return graph

        # 2. Sequential / Parallel Reasoning
        if intent_type == "search":
             # Task 1: Search
             graph.add_node(TaskNode(
                 id="t_search",
                 agent="search_agent",
                 description=f"Retrieve latest data for: {user_input}",
                 inputs={"query": user_input}
             ))
             
             # Task 2: Synthesize (Depends on Task 1)
             graph.add_node(TaskNode(
                 id="t_synth",
                 agent="chat_agent",
                 description="Synthesize search results into coherent response",
                 inputs={"input": user_input, "context": "{{t_search.result}}"},
                 dependencies=["t_search"]
             ))
             
        elif intent_type == "document":
             graph.add_node(TaskNode(
                 id="t_doc",
                 agent="document_agent",
                 description="Query internal RAG vector store",
                 inputs={"query": user_input}
             ))
             graph.add_node(TaskNode(
                 id="t_synth",
                 agent="chat_agent",
                 description="Synthesize document context",
                 inputs={"input": user_input, "context": "{{t_doc.result}}"},
                 dependencies=["t_doc"]
             ))

        elif intent_type == "code":
             graph.add_node(TaskNode(
                 id="t_code",
                 agent="code_agent",
                 description="Generate code block",
                 inputs={"input": user_input}
             ))
             # Verification Task (Parallel or Sequential)
             graph.add_node(TaskNode(
                 id="t_verify",
                 agent="python_repl_agent",
                 description="Verify code syntax and logic",
                 inputs={"code": "{{t_code.result}}"},
                 dependencies=["t_code"]
             ))

        else: # Standard Chat / Reasoning
             graph.add_node(TaskNode(
                 id="t_core",
                 agent="chat_agent",
                 description="Primary LLM reasoning pass",
                 inputs={"input": user_input}
             ))

        # 3. Final Reflection (Universal Pass for V8)
        if complexity >= 2:
            last_id = graph.nodes[-1].id
            graph.add_node(TaskNode(
                id="t_reflect",
                agent="critic_agent",
                description="Final qualitative reflection",
                inputs={"draft": f"{{{{{last_id}.result}}}}", "goal": goal.objective},
                dependencies=[last_id],
                critical=False
            ))

        return graph
