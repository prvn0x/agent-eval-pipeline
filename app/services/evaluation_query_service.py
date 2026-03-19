from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import Evaluation
from app.db.repositories.evaluation_repository import EvaluationRepository


class EvaluationQueryService:
    """Read-only service for fetching evaluation results."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = EvaluationRepository(session)

    async def get_by_conversation(self, conversation_id: str) -> Evaluation | None:
        return await self._repo.get_by_conversation_id(conversation_id)
