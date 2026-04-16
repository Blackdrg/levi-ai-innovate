from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class EventSchema(BaseModel):
    event_type: str
    mission_id: str
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    payload: Dict[str, Any]
    source: str
    validation_hash: Optional[str] = None

class CriticSchema(BaseModel):
    score: float
    confidence: float
    errors: List[str] = []
    validated: bool = False

class MissionCommitEvent(BaseModel):
    mission_id: str
    user_id: str
    objective: str
    response: str
    fidelity: float
    critic_report: Dict[str, Any]
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

class PerceptionResult(BaseModel):
    intent: str
    confidence: float
    entities: Dict[str, Any]
    priority: int = 1
    raw_query: str

class PlannerResult(BaseModel):
    plan_id: str
    tasks: List[Dict[str, Any]]
    estimated_complexity: float
    required_agents: List[str]
    critical_path: List[str]
