"""
backend/services/orchestrator/orchestrator_types.py

Centralized type definitions for the LEVI AI Brain orchestrator pipeline.
"""
import uuid
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union


# ---------------------------------------------------------------------------
# Engine Routing
# ---------------------------------------------------------------------------

class EngineRoute(str, Enum):
    """The three execution paths the Decision Engine can select."""
    LOCAL = "local"   # Zero-cost: greetings, FAQs, simple logic
    TOOL  = "tool"    # Agent-based: image, code, search, custom tools
    API   = "api"     # LLM call: complex reasoning, creative generation, unknown


# ---------------------------------------------------------------------------
# Decision Audit Log
# ---------------------------------------------------------------------------

@dataclass
class DecisionLog:
    """Immutable audit record emitted at the Decision Engine boundary."""
    request_id: str
    user_id: str
    intent: str
    complexity: int
    confidence: float
    route: EngineRoute
    model: str = "none"
    provider: str = "none"
    notes: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "request_id":  self.request_id,
            "user_id":     self.user_id,
            "intent":      self.intent,
            "complexity":  self.complexity,
            "confidence":  self.confidence,
            "route":       self.route.value,
            "model":       self.model,
            "provider":    self.provider,
            "notes":       self.notes,
        }


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

class IntentResult(BaseModel):
    """
    The output of the intent classifier.

    Supported intents
    -----------------
    greeting      - Hello, Hi, Hey, Good morning, etc.
    simple_query  - One-liners with a clear, low-complexity answer
    tool_request  - Explicit tool use: image gen, code, search
    image         - Image / art generation
    code          - Programming / scripting tasks
    search        - Real-time lookup, facts, news
    complex_query - Multi-step reasoning, creative writing, debates
    chat          - General conversational exchange (catch-all)
    unknown       - Cannot be classified; will be routed to API with low confidence
    """
    intent: str = "chat"
    complexity: int = Field(3, ge=1, le=10)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool Contracts & Execution Results
# ---------------------------------------------------------------------------

class ToolResult(BaseModel):
    """
    Ensures every agent/tool returns a predictable structure.
    Strictly prevents "hallucinated actions" by standardized success/failure reporting.
    """
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    agent: str = "unknown"
    latency_ms: int = 0
    total_tokens: int = 0
    retryable: bool = True

class PlanStep(BaseModel):
    """A single deterministic step in a brain execution plan."""
    step_id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:6]}")
    description: str
    agent: str  # e.g., 'chat_agent', 'image_agent'
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    fallback_agent: Optional[str] = "chat_agent"
    critical: bool = True  # If true, failure stops the whole plan

class ExecutionPlan(BaseModel):
    """
    The 'Deterministic Brain' plan. 
    Removes randomness by forcing the AI to define its path BEFORE execution.
    """
    intent: str
    steps: List[PlanStep]
    memory_needed: List[str] = Field(default_factory=list) # e.g., ['user_mood', 'past_topics']
    estimated_complexity: int = 5
    priority: int = 1

class OrchestratorResponse(BaseModel):
    """Final output payload from the orchestrator."""
    response: str
    intent: str
    route: str = EngineRoute.API.value
    plan_executed: List[ToolResult] = Field(default_factory=list)
    session_id: str = ""
    job_ids: List[str] = Field(default_factory=list)
    request_id: str = ""
    latency_total: int = 0
