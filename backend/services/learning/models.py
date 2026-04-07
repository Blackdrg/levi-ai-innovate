from pydantic import BaseModel, Field # type: ignore
from typing import Optional
from datetime import datetime, timezone

class TrainingDataSchema(BaseModel):
    user_message: str
    bot_response: str
    mood: str
    rating: Optional[int] = None
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PromptPerformanceSchema(BaseModel):
    prompt_id: str
    usage_count: int = 0
    avg_rating: float = 0.0

class TrainingJobSchema(BaseModel):
    job_id: str
    status: str # queued, processing, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
