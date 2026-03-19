from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, ConversationStatus
from app.db.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import (
    BatchIngestRequest,
    BatchIngestResponse,
    ConversationCreate,
    ConversationResponse,
)
from app.worker.tasks import evaluate_conversation


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ConversationRepository(session)

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

        evaluate_conversation.apply_async(
            args=[payload.conversation_id],
            queue="evaluations",
        )

        return ConversationResponse(
            conversation_id=payload.conversation_id,
            status=ConversationStatus.PENDING,
            message="Queued for evaluation",
        )

    async def ingest_batch(self, payload: BatchIngestRequest) -> BatchIngestResponse:
        ids = []
        for item in payload.conversations:
            await self.ingest(item)
            ids.append(item.conversation_id)
        return BatchIngestResponse(accepted=len(ids), conversation_ids=ids)
