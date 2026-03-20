from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Annotation(BaseModel):
    type: str
    label: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FeedbackSubmit(BaseModel):
    annotator_id: str
    annotations: list[Annotation] = Field(min_length=1)


class FeedbackResponse(BaseModel):
    conversation_id: str
    annotator_id: str
    accepted: int
    message: str


class AgreementResponse(BaseModel):
    conversation_id: str
    cohen_kappa: float | None
    agreement_level: Literal["poor", "fair", "moderate", "strong", "perfect"]
    routing_decision: Literal["auto_label", "human_review"]
    annotator_count: int
    label_distribution: dict
