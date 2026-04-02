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

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)

class TaskGraph(BaseModel):
    nodes: List[TaskNode] = Field(default_factory=list)
    
    def add_node(self, node: TaskNode):
        self.nodes.append(node)
        
    def to_dict(self):
        return [n.dict() for n in self.nodes]

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)
