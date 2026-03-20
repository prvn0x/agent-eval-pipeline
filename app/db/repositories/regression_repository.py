from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.regression import RegressionAlert


class RegressionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, alert: RegressionAlert) -> RegressionAlert:
        self._session.add(alert)
        await self._session.flush()
        return alert

    async def list_by_version(self, agent_version: str | None = None) -> list[RegressionAlert]:
        q = select(RegressionAlert).order_by(RegressionAlert.created_at.desc())
        if agent_version:
            q = q.where(RegressionAlert.agent_version == agent_version)
        result = await self._session.execute(q)
        return list(result.scalars().all())
