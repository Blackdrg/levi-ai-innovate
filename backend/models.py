# backend/models.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

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
    """
    Unified Feedback Model for AI responses (Chat) and generated assets (Studio/Gallery).
    """
    session_id: Optional[str] = Field(None, max_length=100)
    item_id: Optional[str] = Field(None, max_length=100, description="message_id or image_id")
    item_type: str = Field("chat", description="One of: chat, image, video")
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)
    
    # Metadata for Chat Learning (Optional)
    user_message: Optional[str] = None
    bot_response: Optional[str] = None
    mood: Optional[str] = "neutral"
    
    @field_validator("rating")
    @classmethod
    def validate_rating_val(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

class AdminAdjustCredits(BaseModel):
    user_id: str
    amount: int = Field(..., description="Credits to add (positive) or remove (negative)")

class OrderRequest(BaseModel):
    plan: str  # "pro" or "creator"

class PaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    url: Optional[str] = None
    error: Optional[str] = None