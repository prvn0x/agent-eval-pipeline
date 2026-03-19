from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    latency_ms: int | None = None


class Turn(BaseModel):
    turn_id: int
    role: Literal["user", "assistant"]
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    timestamp: datetime


class OpsReview(BaseModel):
    quality: str
    notes: str | None = None


class Annotation(BaseModel):
    type: str
    label: str
    annotator_id: str
    confidence: float = 1.0


class Feedback(BaseModel):
    user_rating: int | None = Field(default=None, ge=1, le=5)
    ops_review: OpsReview | None = None
    annotations: list[Annotation] = Field(default_factory=list)


class ConversationMetadata(BaseModel):
    total_latency_ms: int | None = None
    mission_completed: bool | None = None


class ConversationCreate(BaseModel):
    conversation_id: str
    agent_version: str
    turns: list[Turn] = Field(min_length=1)
    feedback: Feedback | None = None
    metadata: ConversationMetadata | None = None


class ConversationResponse(BaseModel):
    conversation_id: str
    status: str
    message: str


class BatchIngestRequest(BaseModel):
    conversations: list[ConversationCreate] = Field(min_length=1)


class BatchIngestResponse(BaseModel):
    accepted: int
    conversation_ids: list[str]
