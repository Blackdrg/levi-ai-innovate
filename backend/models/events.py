from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import hashlib
import json

class SovereignEvent(BaseModel):
    """
    Sovereign v16.2 Standard Event Schema.
    Ensures verifiable, structured communication across all micro-services.
    """
    event_type: str
    mission_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any]
    source: str
    validation_hash: Optional[str] = None

    @validator("validation_hash", pre=True, always=True)
    def generate_hash(cls, v, values):
        if v: return v
        # Generate hash if not provided
        payload_str = json.dumps(values.get("payload", {}), sort_keys=True)
        hash_material = f"{values.get('event_type')}:{values.get('mission_id')}:{payload_str}:{values.get('source')}"
        return hashlib.sha256(hash_material.encode()).hexdigest()

class CriticResult(BaseModel):
    """
    Reflection Engine Output Contract.
    Used to gate memory commits and evolution training.
    """
    score: float = Field(0.0, ge=0.0, le=1.0)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    fidelity: float = Field(0.0, ge=0.0, le=1.0) # REQUIRED
    errors: List[str] = Field(default_factory=list)
    validated: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ModuleIO(BaseModel):
    """Base for Module I/O Contracts"""
    mission_id: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: str = "PENDING" # PENDING, PROCESSING, COMPLETED, FAILED
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    latency_ms: float = 0.0
    error: Optional[str] = None
    source: str = "unknown"

class PerceptionContract(ModuleIO):
    """Refined input for environmental/user perception."""
    user_id: str
    raw_input: str
    context: Dict[str, Any] = Field(default_factory=dict)

class PlannerContract(ModuleIO):
    """Mission DAG/WaveScheduler output."""
    goal: str
    graph: Dict[str, Any] # Serialized TaskGraph
    wave_count: int
    complexity: int

class AgentContract(ModuleIO):
    """Single agent execution contract."""
    agent_id: str
    tool: str
    tool_input: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None

class MemoryContract(ModuleIO):
    """Memory lifecycle: Commit, Recall, Distill."""
    operation: str # COMMIT, RECALL, DISTILL
    tier: str # T1, T2, T3, T4, T5
    payload: Dict[str, Any]

class EvolutionContract(ModuleIO):
    """Autonomous learning & model update."""
    source_data_ids: List[str]
    training_type: str # LORA, PPO, DISTILL
    reward: float = 0.0
    metrics: Dict[str, float] = Field(default_factory=dict)

class SystemPulseEvent(BaseModel):
    """Event emitted for periodic system tasks (replacement for cron)."""
    pulse_type: str # HEARTBEAT, DAILY_RESET, WEEKLY_CALIBRATION
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TaskManagerContract(BaseModel):
    """Central Task Manager contract for unified execution."""
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    module: str
    action: str
    payload: Dict[str, Any]
    retries: int = 3
    timeout: int = 60
    status: str = "QUEUED"
