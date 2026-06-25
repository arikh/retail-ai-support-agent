"""
Phase 8: Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(default=None)
    prompt_variant: Optional[str] = Field(default="v3")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    latency_ms: float


class FeedbackRequest(BaseModel):
    session_id: str
    user_query: str
    agent_response: str
    rating: int = Field(..., ge=0, le=1)
    comment: Optional[str] = Field(default="")


class FeedbackResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    model: str
    version: str
