import logging
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.evaluation import Evaluation
from app.db.models.regression import RegressionAlert
from app.db.repositories.regression_repository import RegressionRepository
from app.schemas.regression import RegressionAlertItem, RegressionAlertsResponse

logger = logging.getLogger(__name__)

_WINDOW_SIZE = 50        # last N evaluations per agent version
_FAILURE_THRESHOLD = 0.2 # alert when >20% of recent evals are failures
_PASS_SCORE = 0.7        # evaluation score below this = failure
_ALERT_COOLDOWN_MINUTES = 10  # don't re-fire an alert for the same version within this window


class RegressionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RegressionRepository(session)

    async def check_all_versions(self) -> list[RegressionAlert]:
        """Check recent evaluations for every known agent version; fire alerts on regressions."""
        version_rows = await self._session.execute(
            select(distinct(Conversation.agent_version))
        )
        versions = list(version_rows.scalars().all())

        alerts = []
        for version in versions:
            alert = await self._check_version(version)
            if alert:
                alerts.append(alert)
        return alerts

    async def _check_version(self, agent_version: str) -> RegressionAlert | None:
        rows = await self._session.execute(
            select(Evaluation)
            .join(Conversation, Evaluation.conversation_id == Conversation.id)
            .where(Conversation.agent_version == agent_version)
            .order_by(Evaluation.created_at.desc())
            .limit(_WINDOW_SIZE)
        )
        evals = list(rows.scalars().all())
        if not evals:
            return None

        failures = sum(
            1 for e in evals
            if e.overall_score is None or e.overall_score < _PASS_SCORE
        )
        failure_rate = round(failures / len(evals), 3)

        if failure_rate <= _FAILURE_THRESHOLD:
            return None

        # Cooldown: don't re-fire if an alert already exists for this version within the window
        cooldown_cutoff = datetime.now(timezone.utc) - timedelta(minutes=_ALERT_COOLDOWN_MINUTES)
        recent = await self._session.execute(
            select(RegressionAlert)
            .where(RegressionAlert.agent_version == agent_version)
            .where(RegressionAlert.created_at >= cooldown_cutoff)
            .limit(1)
        )
        if recent.scalars().first():
            return None

        logger.warning(
            "Regression detected for %s: %.0f%% failure rate over last %d evals",
            agent_version, failure_rate * 100, len(evals),
        )
        alert = RegressionAlert(
            id=f"reg_{uuid.uuid4().hex[:8]}",
            agent_version=agent_version,
            failure_rate=failure_rate,
            window_size=len(evals),
            threshold=_FAILURE_THRESHOLD,
        )
        await self._repo.save(alert)
        return alert

    async def list_alerts(self, agent_version: str | None = None) -> RegressionAlertsResponse:
        alerts = await self._repo.list_by_version(agent_version)
        return RegressionAlertsResponse(
            total=len(alerts),
            alerts=[
                RegressionAlertItem(
                    id=a.id,
                    agent_version=a.agent_version,
                    failure_rate=a.failure_rate,
                    window_size=a.window_size,
                    threshold=a.threshold,
                    created_at=a.created_at,
                )
                for a in alerts
            ],
        )
