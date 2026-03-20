from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SuggestionItem(BaseModel):
    id: str
    agent_version: str
    pattern_type: str
    pattern_summary: str
    suggestion_text: str
    rationale: str | None
    confidence: float | None
    category: Literal["prompt", "tool", "training"]
    occurrence_count: int
    created_at: datetime


class SuggestionsResponse(BaseModel):
    agent_version: str | None
    total: int
    suggestions: list[SuggestionItem]
