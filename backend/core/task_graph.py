"""
Sovereign Task Graph v8.
Defines the structure of cognitive missions with explicit dependencies.
"""

import logging
from collections import deque
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from .orchestrator_types import TaskExecutionContract

logger = logging.getLogger(__name__)

class TaskNode(BaseModel):
    id: str
    agent: str
    description: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list) # IDs of parent tasks
    critical: bool = True
    retry_count: int = 2
    retry_policy: str = "exponential_backoff"
    retry_strategy: str = "exp_backoff_jitter"
    strict_schema: bool = True
    fallback_node_id: Optional[str] = None # ID of the node to run if this fails
    fallback_output: Optional[Dict[str, Any]] = None
    compensation_action: Optional[str] = None
    condition: Optional[str] = None # Lambda-like string to evaluate before running
    tier: str = "L2" # L1, L2, L3, L4 (Tiers for resource/model mapping)
    result: Optional[Any] = None # Added for active state tracking
    contract: Optional[TaskExecutionContract] = None
    circuit_breaker: Dict[str, Any] = Field(
        default_factory=lambda: {"fail_threshold": 3, "cooldown_ms": 10000}
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)

class TaskGraph(BaseModel):
    nodes: List[TaskNode] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict) # Track results internally
    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "strict_schema": True,
            "retry_strategy": "exp_backoff_jitter",
            "baseline_tag": "v14.0.0-STABLE-BASELINE",
        }
    )

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

    def validate_dag(self, max_depth: Optional[int] = None) -> None:
        self._analyze_dag(max_depth=max_depth)

    def max_depth(self) -> int:
        return self._analyze_dag()["max_depth"]

    def _analyze_dag(self, max_depth: Optional[int] = None) -> Dict[str, Any]:
        nodes_map = {n.id: n for n in self.nodes}
        if len(nodes_map) != len(self.nodes):
            duplicates = []
            seen: Set[str] = set()
            for node in self.nodes:
                if node.id in seen:
                    duplicates.append(node.id)
                seen.add(node.id)
            raise ValueError(f"Duplicate task nodes detected: {sorted(set(duplicates))}")

        if not self.nodes:
            raise ValueError("Task graph cannot be empty.")

        inbound = {node.id: len(node.dependencies) for node in self.nodes}
        outbound: Dict[str, List[str]] = {node.id: [] for node in self.nodes}
        undirected: Dict[str, Set[str]] = {node.id: set() for node in self.nodes}

        for node in self.nodes:
            for dep in node.dependencies:
                if dep not in nodes_map:
                    raise ValueError(f"Node {node.id} depends on missing node {dep}")
                outbound[dep].append(node.id)
                undirected[node.id].add(dep)
                undirected[dep].add(node.id)

        if len(self.nodes) > 1:
            orphans = [
                node.id for node in self.nodes if not node.dependencies and not outbound[node.id]
            ]
            if orphans:
                raise ValueError(f"Orphan nodes detected: {orphans}")

        queue = deque(sorted(node_id for node_id, degree in inbound.items() if degree == 0))
        visited: List[str] = []
        depth_map: Dict[str, int] = {node_id: 1 for node_id in queue}

        while queue:
            node_id = queue.popleft()
            visited.append(node_id)
            for child in outbound[node_id]:
                inbound[child] -= 1
                depth_map[child] = max(depth_map.get(child, 1), depth_map.get(node_id, 1) + 1)
                if inbound[child] == 0:
                    queue.append(child)

        if len(visited) != len(self.nodes):
            unresolved = [node_id for node_id, degree in inbound.items() if degree > 0]
            raise ValueError(f"Circular dependencies detected: {unresolved}")

        root_id = self.nodes[0].id
        connected = set()
        pending = deque([root_id])
        while pending:
            node_id = pending.popleft()
            if node_id in connected:
                continue
            connected.add(node_id)
            pending.extend(sorted(undirected[node_id] - connected))

        if len(connected) != len(self.nodes):
            disconnected = sorted(set(nodes_map) - connected)
            raise ValueError(f"Disconnected nodes detected: {disconnected}")

        if max_depth is not None and depth_map and max(depth_map.values()) > max_depth:
            raise ValueError(f"DAG depth {max(depth_map.values())} exceeds limit {max_depth}")

        return {
            "max_depth": max(depth_map.values()) if depth_map else 0,
            "visited": visited,
            "depth_map": depth_map,
        }

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)
