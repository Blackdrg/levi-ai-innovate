"""
backend/models/orchestrator_types.py

Sovereign Mind v7 Typed Contracts.
Ensures consistency between API -> Brain -> Engines.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid

class ToolResult(BaseModel):
    agent: str
    success: bool
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    cost_score: int = 0

class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:6]}")
    description: str
    agent: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    critical: bool = True

class ExecutionPlan(BaseModel):
    intent: str
    steps: List[PlanStep]
    complexity_level: int = 2
    is_sensitive: bool = False

class OrchestratorResponse(BaseModel):
    response: str
    intent: str
    route: str = "api"
    plan_executed: List[ToolResult] = Field(default_factory=list)
    request_id: str = ""
    latency_total: int = 0
