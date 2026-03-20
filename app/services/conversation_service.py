import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.conversation import Conversation, ConversationStatus
from app.db.models.feedback import AnnotationRecord
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.feedback_repository import FeedbackRepository
from app.schemas.conversation import (
    BatchIngestRequest,
    BatchIngestResponse,
    ConversationCreate,
    ConversationResponse,
)


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ConversationRepository(session)
        self._settings = get_settings()

    async def ingest(self, payload: ConversationCreate) -> ConversationResponse:
        conversation = Conversation(
            id=payload.conversation_id,
            agent_version=payload.agent_version,
            turns=[t.model_dump(mode="json") for t in payload.turns],
            feedback=payload.feedback.model_dump(mode="json") if payload.feedback else None,
            conv_metadata=payload.metadata.model_dump(mode="json") if payload.metadata else None,
            status=ConversationStatus.PENDING,
        )
        await self._repo.create(conversation)
        await self._import_inline_annotations(payload)

        if self._settings.sync_eval:
            from app.services.evaluation_service import EvaluationService
            await EvaluationService(self._session).run(payload.conversation_id)
        else:
            from app.worker.tasks import evaluate_conversation
            evaluate_conversation.apply_async(
                args=[payload.conversation_id],
                queue="evaluations",
            )

        return ConversationResponse(
            conversation_id=payload.conversation_id,
            status=ConversationStatus.PENDING,
            message="Queued for evaluation",
        )

    async def _import_inline_annotations(self, payload: ConversationCreate) -> None:
        """Auto-import annotations embedded in the conversation payload into AnnotationRecord."""
        if not payload.feedback or not payload.feedback.annotations:
            return

        grouped: dict[str, list[dict]] = defaultdict(list)
        for ann in payload.feedback.annotations:
            grouped[ann.annotator_id].append(ann.model_dump())

        feedback_repo = FeedbackRepository(self._session)
        for annotator_id, anns in grouped.items():
            record = AnnotationRecord(
                id=f"ann_{uuid.uuid4().hex[:8]}",
                conversation_id=payload.conversation_id,
                annotator_id=annotator_id,
                annotations=anns,
            )
            await feedback_repo.save_annotation(record)

        if len(grouped) >= 2:
            from app.services.feedback_service import FeedbackService
            await FeedbackService(self._session).recompute_agreement(payload.conversation_id)

    async def ingest_batch(self, payload: BatchIngestRequest) -> BatchIngestResponse:
        ids = []
        for item in payload.conversations:
            await self.ingest(item)
            ids.append(item.conversation_id)
        return BatchIngestResponse(accepted=len(ids), conversation_ids=ids)
