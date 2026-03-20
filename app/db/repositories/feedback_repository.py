from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.feedback import AnnotationRecord, AgreementRecord


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_annotation(self, record: AnnotationRecord) -> AnnotationRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def save_agreement(self, record: AgreementRecord) -> AgreementRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_annotations_for_conversation(
        self, conversation_id: str
    ) -> list[AnnotationRecord]:
        result = await self._session.execute(
            select(AnnotationRecord).where(
                AnnotationRecord.conversation_id == conversation_id
            )
        )
        return list(result.scalars().all())

    async def get_agreement(self, conversation_id: str) -> AgreementRecord | None:
        result = await self._session.execute(
            select(AgreementRecord).where(
                AgreementRecord.conversation_id == conversation_id
            ).order_by(AgreementRecord.created_at.desc())
        )
        return result.scalars().first()
