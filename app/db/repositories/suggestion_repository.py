from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.suggestion import ImprovementSuggestion


class SuggestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: ImprovementSuggestion) -> ImprovementSuggestion:
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_by_agent_version(self, agent_version: str) -> list[ImprovementSuggestion]:
        result = await self._session.execute(
            select(ImprovementSuggestion)
            .where(ImprovementSuggestion.agent_version == agent_version)
            .order_by(ImprovementSuggestion.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[ImprovementSuggestion]:
        result = await self._session.execute(
            select(ImprovementSuggestion).order_by(ImprovementSuggestion.created_at.desc())
        )
        return list(result.scalars().all())
