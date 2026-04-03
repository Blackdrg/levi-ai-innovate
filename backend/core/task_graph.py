"""
Sovereign Task Graph v8.
Defines the structure of cognitive missions with explicit dependencies.
"""

import logging
from typing import List, Dict, Any, Optional
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
    result: Optional[Any] = None # Added for active state tracking

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)

class TaskGraph(BaseModel):
    nodes: List[TaskNode] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict) # Track results internally

    def add_node(self, node: TaskNode):
        self.nodes.append(node)

    def get_ready_tasks(self) -> List[TaskNode]:
        """Returns nodes whose dependencies are all met and not yet started."""
        return [
            n for n in self.nodes 
            if n.result is None and all(dep in self.results for dep in n.dependencies)
        ]

    def mark_complete(self, node_id: str, result: Any):
        """Marks a task as complete and stores the result."""
        for n in self.nodes:
            if n.id == node_id:
                n.result = result
                self.results[node_id] = result
                break

    def is_complete(self) -> bool:
        """Returns True if all nodes have results."""
        return all(n.result is not None for n in self.nodes)

    def to_dict(self):
        return [n.dict() for n in self.nodes]

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)
