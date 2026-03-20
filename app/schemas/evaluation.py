from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class IssueDetected(BaseModel):
    type: str
    severity: Literal["warning", "critical"]
    description: str


class ImprovementSuggestion(BaseModel):
    type: Literal["prompt", "tool", "training"]
    suggestion: str
    rationale: str
    confidence: float


class ToolEvaluation(BaseModel):
    execution_success: bool | None = None
    total_tools: int | None = None
    tool_failures: int | None = None
    selection_accuracy: float | None = None
    parameter_accuracy: float | None = None


class EvaluationScores(BaseModel):
    overall: float
    response_quality: float | None = None
    tool_accuracy: float | None = None
    coherence: float | None = None


class EvaluationResponse(BaseModel):
    evaluation_id: str
    conversation_id: str
    status: str
    scores: EvaluationScores
    tool_evaluation: ToolEvaluation | None = None
    issues_detected: list[IssueDetected] = []
    improvement_suggestions: list[ImprovementSuggestion] = []
    created_at: datetime | None = None
