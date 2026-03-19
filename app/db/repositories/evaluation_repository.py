from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.evaluation import Evaluation


class EvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, evaluation: Evaluation) -> Evaluation:
        self._session.add(evaluation)
        await self._session.flush()
        return evaluation

    async def get_by_conversation_id(self, conversation_id: str) -> Evaluation | None:
        result = await self._session.execute(
            select(Evaluation).where(Evaluation.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()
