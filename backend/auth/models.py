"""
Sovereign Shield Auth Models v8.
Pydantic schemas for user and session representation.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    uid: str
    email: Optional[EmailStr] = None
    username: str

class UserProfile(UserBase):
    tier: str = "free"
    credits: int = 10
    created_at: datetime
    last_active: datetime
    jti: Optional[str] = None
    tier_config: Dict[str, Any] = Field(default_factory=dict)

    def dict(self, *args, **kwargs):
        # Override for compatibility with older pydantic if needed
        return super().model_dump(*args, **kwargs)

class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
