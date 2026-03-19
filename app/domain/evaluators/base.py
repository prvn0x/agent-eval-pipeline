from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.schemas.conversation import ConversationCreate
from app.schemas.evaluation import IssueDetected, ImprovementSuggestion


@dataclass
class EvaluatorResult:
    evaluator_name: str
    score: float | None
    issues: list[IssueDetected] = field(default_factory=list)
    suggestions: list[ImprovementSuggestion] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BaseEvaluator(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def evaluate(self, conversation: ConversationCreate) -> EvaluatorResult: ...
