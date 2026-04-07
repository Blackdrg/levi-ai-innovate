"""
backend/services/orchestrator/orchestrator_types.py

Centralized type definitions for the LEVI AI Brain orchestrator pipeline.
"""
import uuid
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Generic, TypeVar


# ---------------------------------------------------------------------------
# Engine Routing
# ---------------------------------------------------------------------------

class EngineRoute(str, Enum):
    """The three execution paths the Decision Engine can select."""
    LOCAL = "local"   # Zero-cost: greetings, FAQs, simple logic
    TOOL  = "tool"    # Agent-based: image, code, search, custom tools
    API   = "api"     # LLM call: complex reasoning, creative generation, unknown


class BrainMode(str, Enum):
    """v14.0 Cognitive Strategy Modes."""
    FAST = "FAST"
    BALANCED = "BALANCED"
    DEEP = "DEEP"
    RESEARCH = "RESEARCH"
    SECURE = "SECURE"


class MemoryPolicy(BaseModel):
    """Tiered memory activation policy."""
    redis: bool = True
    postgres: bool = True
    neo4j: bool = False
    faiss: bool = True


class ExecutionPolicy(BaseModel):
    """Runtime constraints for the executor."""
    parallel_waves: int = 2
    max_retries: int = 1
    sandbox_required: bool = False


class LLMPolicy(BaseModel):
    """LLM routing constraints."""
    local_only: bool = True
    cloud_fallback: bool = False


class IntentNode(BaseModel):
    id: str
    label: str
    entity: Optional[str] = None
    confidence: float = 1.0


class IntentEdge(BaseModel):
    source: str
    target: str
    relation: str


class IntentGraph(BaseModel):
    nodes: List[IntentNode] = Field(default_factory=list)
    edges: List[IntentEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FailureType(str, Enum):
    LLM_ERROR = "LLM_ERROR"
    TOOL_FAILURE = "TOOL_FAILURE"
    DAG_CONFLICT = "DAG_CONFLICT"
    MEMORY_MISMATCH = "MEMORY_MISMATCH"


class FailureAction(BaseModel):
    action: str  # retry, fallback, regenerate, resync, abort
    params: Dict[str, Any] = Field(default_factory=dict)


class BrainDecision(BaseModel):

    """
    The unified v14.0 Brain Decision Output.
    Centrally governs all system behavior.
    """
    mode: BrainMode = BrainMode.BALANCED
    enable_agents: Dict[str, bool] = Field(default_factory=lambda: {
        "planner": True,
        "critic": False,
        "retrieval": False
    })
    memory_policy: MemoryPolicy = Field(default_factory=MemoryPolicy)
    execution_policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    llm_policy: LLMPolicy = Field(default_factory=LLMPolicy)
    risk_level: float = 0.0
    complexity_score: float = 0.0



# ---------------------------------------------------------------------------
# Decision Audit Log
# ---------------------------------------------------------------------------

@dataclass
class DecisionLog:
    """Immutable audit record emitted at the Decision Engine boundary."""
    request_id: str
    user_id: str
    intent_type: str
    complexity_level: int
    confidence_score: float
    estimated_cost_weight: str
    route: EngineRoute
    model: str = "none"
    provider: str = "none"
    notes: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "request_id":            self.request_id,
            "user_id":               self.user_id,
            "intent_type":           self.intent_type,
            "complexity_level":      self.complexity_level,
            "confidence_score":      self.confidence_score,
            "estimated_cost_weight": self.estimated_cost_weight,
            "route":                 self.route.value,
            "model":                 self.model,
            "provider":              self.provider,
            "notes":                 self.notes,
        }


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

class IntentResult(BaseModel):
    """
    The output of the intent classifier.
    """
    model_config = {"protected_namespaces": ()}
    
    intent_type: str = "chat"
    complexity_level: int = Field(2, ge=0, le=3)
    estimated_cost_weight: str = "medium" # low, medium, high
    confidence_score: float = Field(0.8, ge=0.0, le=1.0)
    is_sensitive: bool = False  # If true, forces local execution
    parameters: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool Contracts & Execution Results
# ---------------------------------------------------------------------------

class ToolResult(BaseModel):
    """
    Ensures every agent/tool returns a predictable structure.
    Strictly prevents "hallucinated actions" by standardized success/failure reporting.
    """
    model_config = {"protected_namespaces": ()}
    
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    agent: str = "unknown"
    latency_ms: int = 0
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    fidelity_score: float = Field(1.0, ge=0.0, le=1.0)
    cost_score: int = 0
    total_tokens: int = 0
    retryable: bool = True


class PlanStep(BaseModel):
    """A single deterministic step in a brain execution plan."""
    model_config = {"protected_namespaces": ()}
    
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
    model_config = {"protected_namespaces": ()}
    
    intent: str
    steps: List[PlanStep]
    memory_needed: List[str] = Field(default_factory=list) # e.g., ['user_mood', 'past_topics']
    complexity_level: int = 2
    is_sensitive: bool = False # Flag for local-only shield
    priority: int = 1

class OrchestratorResponse(BaseModel):
    """Final output payload from the orchestrator."""
    model_config = {"protected_namespaces": ()}
    
    response: str
    intent: str
    route: str = EngineRoute.API.value
    plan_executed: List[ToolResult] = Field(default_factory=list)
    session_id: str = ""
    job_ids: List[str] = Field(default_factory=list)
    request_id: str = ""
    latency_total: int = 0

# ---------------------------------------------------------------------------
# V8 Agent Contracts (Brain-First Cognitive Evolution)
# ---------------------------------------------------------------------------

DataT = TypeVar("DataT", bound=Any)

class AgentResult(BaseModel, Generic[DataT]):
    """
    Standardized result for all Sovereign v8 Agents.
    Enforces Brain-level validation for mission outputs.
    """
    model_config = {"protected_namespaces": ()}
    
    success: bool = True
    message: str = ""
    data: Optional[DataT] = None
    agent: str = "unknown"
    error: Optional[str] = None
    latency_ms: float = 0.0
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    citations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Backward compatibility alias
    @property
    def id(self) -> str:
        return self.agent

class AgentBase:
    """
    Base Contract for v8 Autonomous Systems.
    """
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"v8.agent.{name.lower()}")

# ---------------------------------------------------------------------------
# API Request / Response Schemas (Moved from backend/models.py)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    "ignore previous", "ignore all previous", "forget previous",
    "new persona", "pretend you are", "jailbreak", "override previous",
    "system:", "assistant:", "user:", "disregard"
]

def sanitize_text_field(v: str) -> str:
    if v:
        v_lower = v.lower()
        for pattern in _INJECTION_PATTERNS:
            if pattern in v_lower:
                raise ValueError(f"Potential prompt injection detected: {pattern}")
    return v

class Query(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field("Unknown", max_length=100)
    mood: Optional[str] = Field("neutral", max_length=50)
    topic: Optional[str] = Field(None, max_length=50)
    lang: Optional[str] = Field("en", max_length=10)
    custom_bg: Optional[str] = Field(None)
    top_k: int = Field(5, ge=1, le=20)

    @field_validator("text", "author", "mood", "topic")
    @classmethod
    def sanitize(cls, v):
        return sanitize_text_field(v)

class ChatMessage(BaseModel):
    session_id: str = Field(..., max_length=100)
    message: str = Field(..., max_length=1000)
    lang: Optional[str] = Field("en", max_length=10)
    mood: Optional[str] = Field("", max_length=50)
    persona_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def sanitize_msg(cls, v):
        return sanitize_text_field(v)

class PersonaCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: str = Field(..., max_length=2000)
    avatar_url: Optional[str] = Field(None, max_length=500)
    is_public: bool = True

    @field_validator("name", "description", "system_prompt")
    @classmethod
    def sanitize_persona(cls, v):
        return sanitize_text_field(v)

class ContentRequest(BaseModel):
    content_type: str = Field(..., alias="type")
    topic: str
    tone: str = "inspiring"
    depth: str = "high"
    language: str = "English"

    model_config = {
        "populate_by_name": True
    }

class FeedbackRequest(BaseModel):
    session_id: Optional[str] = Field(None, max_length=100)
    item_id: Optional[str] = Field(None, max_length=100, description="message_id or image_id")
    item_type: str = Field("chat", description="One of: chat, image, video")
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)
    user_message: Optional[str] = None
    bot_response: Optional[str] = None
    mood: Optional[str] = "neutral"
    
    @field_validator("rating")
    @classmethod
    def validate_rating_val(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v
