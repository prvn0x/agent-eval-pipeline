from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.regression import RegressionAlertsResponse
from app.services.regression_service import RegressionService

router = APIRouter(prefix="/regressions", tags=["Regressions"])


@router.post("/check", response_model=RegressionAlertsResponse)
async def check_regressions(
    db: AsyncSession = Depends(get_db),
) -> RegressionAlertsResponse:
    """Run regression check across all agent versions and return all current alerts."""
    service = RegressionService(db)
    await service.check_all_versions()
    await db.commit()
    return await service.list_alerts()


@router.get("", response_model=RegressionAlertsResponse)
async def list_regressions(
    agent_version: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RegressionAlertsResponse:
    """List all regression alerts, optionally filtered by agent_version."""
    return await RegressionService(db).list_alerts(agent_version)
