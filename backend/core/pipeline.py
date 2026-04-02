import dataclasses
from typing import Any, Dict, List, Optional

@dataclasses.dataclass
class FlowState:
    """Represents the global state of an execution flow."""
    user_id: str
    query: str
    intent: Optional[str] = None
    plan: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    engine_results: Dict[str, Any] = dataclasses.field(default_factory=dict)
    final_response: Optional[str] = None
    error: Optional[str] = None

class FlowPipeline:
    """Manages the lifecycle of a query from User -> Brain -> Plan -> Engines -> Merge -> Response"""
    
    def __init__(self, state: FlowState):
        self.state = state
        self.history_log = []

    def log(self, step: str, message: str):
        """Append to flow history for observability."""
        self.history_log.append(f"[{step}] {message}")
        print(f"[Pipeline] {self.state.user_id} - {step}: {message}")
