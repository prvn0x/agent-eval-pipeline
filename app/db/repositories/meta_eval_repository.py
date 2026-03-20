from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meta_eval import MetaEvalReport


class MetaEvalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: MetaEvalReport) -> MetaEvalReport:
        self._session.add(report)
        await self._session.flush()
        return report

    async def get_latest(self) -> MetaEvalReport | None:
        result = await self._session.execute(
            select(MetaEvalReport).order_by(MetaEvalReport.created_at.desc())
        )
        return result.scalars().first()
