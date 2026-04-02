from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum
import uuid

class EngineRoute(str, Enum):
    LOCAL = "local"
    API = "api"
    CACHE = "cache"
    BLOCKED = "blocked"

class IntentResult(BaseModel):
    intent_type: str
    complexity_level: int = 1
    confidence_score: float = 1.0
    estimated_cost_weight: str = "medium"
    is_sensitive: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ToolResult(BaseModel):
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    agent: str = ""
    error: Optional[str] = None
    latency_ms: int = 0
    citations: List[str] = Field(default_factory=list)

class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:6]}")
    objective: str
    success_criteria: List[str] = Field(default_factory=list)
    priority: str = "medium"
    state: str = "active"

class TaskNode(BaseModel):
    id: str
    agent: str
    description: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    critical: bool = True
    retry_count: int = 2
