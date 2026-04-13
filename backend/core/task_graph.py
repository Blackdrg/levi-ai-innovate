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

    def get_execution_waves(self) -> List[List[TaskNode]]:
        """
        Sovereign v15.0: Cognitive Wave Partitioning.
        Groups tasks into parallel execution waves based on dependency resolution.
        """
        waves = []
        # Copy inbound degrees
        inbound = {node.id: len(node.dependencies) for node in self.nodes}
        outbound: Dict[str, List[str]] = {node.id: [] for node in self.nodes}
        for node in self.nodes:
            for dep in node.dependencies:
                outbound[dep].append(node.id)

        # Nodes with no dependencies are Level 0
        current_wave_ids = [node.id for node in self.nodes if inbound[node.id] == 0]
        
        nodes_map = {n.id: n for n in self.nodes}
        
        while current_wave_ids:
            waves.append([nodes_map[nid] for nid in sorted(current_wave_ids)])
            next_wave_ids = []
            for node_id in current_wave_ids:
                for child_id in outbound[node_id]:
                    inbound[child_id] -= 1
                    if inbound[child_id] == 0:
                        next_wave_ids.append(child_id)
            current_wave_ids = next_wave_ids
            
        return waves

    def generate_mermaid(self) -> str:
        """
        Generates a Mermaid JS representation of the task graph for visualization.
        """
        lines = ["graph TD"]
        # Define nodes with styles
        for node in self.nodes:
            label = f"{node.id}['{node.agent}<br/>{node.description}']"
            lines.append(f"    {label}")
            if node.critical:
                lines.append(f"    style {node.id} stroke:#f66,stroke-width:2px")
            
        # Define edges
        for node in self.nodes:
            for dep in node.dependencies:
                lines.append(f"    {dep} --> {node.id}")
                
        return "\n".join(lines)

    def estimate_cost(self) -> float:
        """
        Sovereign v14.2.0: Predictive CU (Compute Unit) Solver.
        Calculates total complexity weight for billing and resource allocation.
        """
        AGENT_WEIGHTS = {
            "search_agent": 2.0,
            "browser_agent": 4.0,
            "code_agent": 5.0,
            "python_repl_agent": 3.0,
            "image_agent": 10.0,
            "video_agent": 50.0,
            "chat_agent": 1.0,
            "critic_agent": 1.5,
            "consensus_agent": 1.2,
            "relation_agent": 2.5
        }
        total = 0.0
        for node in self.nodes:
            weight = AGENT_WEIGHTS.get(node.agent, 1.0)
            # Complexity scales with retries and criticality
            node_cost = weight * (1 + (node.retry_count * 0.2))
            if node.critical:
                node_cost *= 1.2
            total += node_cost
        
        return round(total, 2)

    def is_complete(self) -> bool:
        """Returns True if all nodes have results."""
        return all(n.result is not None for n in self.nodes)

    def to_dict(self):
        return [n.dict() for n in self.nodes]

    def validate_dag(self, max_depth: Optional[int] = None) -> None:
        analysis = self._analyze_dag(max_depth=max_depth)
        if max_depth is not None and analysis["max_depth"] > max_depth:
            self._flatten_dag(analysis["depth_map"], max_depth)

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

        # Depth check removed here, handled in validate_dag
        return {
            "max_depth": max(depth_map.values()) if depth_map else 0,
            "visited": visited,
            "depth_map": depth_map,
        }

    def _flatten_dag(self, depth_map: Dict[str, int], max_depth: int):
        deep_nodes = [node for node in self.nodes if depth_map.get(node.id, 1) >= max_depth]
        if not deep_nodes:
            return

        shallow_nodes = [node for node in self.nodes if depth_map.get(node.id, 1) < max_depth]
        
        shallow_deps = set()
        for node in deep_nodes:
            for dep in node.dependencies:
                if depth_map.get(dep, 1) < max_depth:
                    shallow_deps.add(dep)
                    
        sub_dag_node = TaskNode(
            id="t_sub_dag_batch",
            agent="meta_planner_agent",
            description=f"Batched sub-DAG execution for {len(deep_nodes)} nodes",
            dependencies=list(shallow_deps),
            critical=True,
            metadata={"batched_nodes": [n.model_dump() for n in deep_nodes]}
        )
        
        shallow_nodes.append(sub_dag_node)
        self.nodes = shallow_nodes

    def dict(self, *args, **kwargs):
        return super().model_dump(*args, **kwargs)
