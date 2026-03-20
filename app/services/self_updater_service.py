import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.conversation import Conversation
from app.db.models.evaluation import Evaluation
from app.db.models.suggestion import ImprovementSuggestion
from app.db.repositories.suggestion_repository import SuggestionRepository
from app.domain.self_updater.pattern_detector import detect_patterns
from app.domain.self_updater.suggestion_generator import generate_suggestions
from app.schemas.suggestion import SuggestionItem, SuggestionsResponse

logger = logging.getLogger(__name__)

_LOW_SCORE_THRESHOLD = 0.9


class SelfUpdaterService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SuggestionRepository(session)
        self._settings = get_settings()

    async def run(self, agent_version: str) -> int:
        evaluations = await self._fetch_low_score_evals(agent_version)
        if not evaluations:
            logger.info("No low-score evaluations for version %s", agent_version)
            return 0

        patterns = detect_patterns(evaluations, self._settings.self_updater_min_occurrences)
        if not patterns:
            logger.info("No recurring patterns (threshold=%d) for %s",
                        self._settings.self_updater_min_occurrences, agent_version)
            return 0

        raw = await generate_suggestions(patterns, self._settings)

        saved = 0
        # zip with original patterns for reliable occurrence counts — LLM may rename pattern_type
        for item, pattern in zip(raw, patterns):
            record = ImprovementSuggestion(
                id=f"sug_{uuid.uuid4().hex[:8]}",
                agent_version=agent_version,
                pattern_type=pattern.pattern_type,
                pattern_summary="; ".join(pattern.example_issues) if pattern.example_issues else pattern.pattern_type,
                suggestion_text=item.get("suggestion", ""),
                category=item.get("category", "training"),
                occurrence_count=pattern.occurrences,
            )
            await self._repo.save(record)
            saved += 1

        return saved

    async def list_suggestions(self, agent_version: str | None) -> SuggestionsResponse:
        if agent_version:
            records = await self._repo.list_by_agent_version(agent_version)
        else:
            records = await self._repo.list_all()

        items = [
            SuggestionItem(
                id=r.id,
                agent_version=r.agent_version,
                pattern_type=r.pattern_type,
                pattern_summary=r.pattern_summary,
                suggestion_text=r.suggestion_text,
                category=r.category,
                occurrence_count=r.occurrence_count,
                created_at=r.created_at,
            )
            for r in records
        ]
        return SuggestionsResponse(agent_version=agent_version, total=len(items), suggestions=items)

    async def _fetch_low_score_evals(self, agent_version: str) -> list[Evaluation]:
        result = await self._session.execute(
            select(Evaluation)
            .join(Conversation, Evaluation.conversation_id == Conversation.id)
            .where(Conversation.agent_version == agent_version)
        )
        all_evals = result.scalars().all()
        return [
            ev for ev in all_evals
            if ev.issues_detected
            or (ev.overall_score is not None and ev.overall_score < _LOW_SCORE_THRESHOLD)
        ]
