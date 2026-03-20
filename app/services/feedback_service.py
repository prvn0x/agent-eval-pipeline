import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.feedback import AnnotationRecord, AgreementRecord
from app.db.repositories.feedback_repository import FeedbackRepository
from app.domain.feedback.annotator import cohen_kappa, kappa_to_level, routing_decision
from app.schemas.feedback import AgreementResponse, FeedbackResponse, FeedbackSubmit


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = FeedbackRepository(session)
        self._settings = get_settings()

    async def submit(self, conversation_id: str, payload: FeedbackSubmit) -> FeedbackResponse:
        record = AnnotationRecord(
            id=f"ann_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            annotator_id=payload.annotator_id,
            annotations=[a.model_dump() for a in payload.annotations],
        )
        await self._repo.save_annotation(record)
        await self.recompute_agreement(conversation_id)

        return FeedbackResponse(
            conversation_id=conversation_id,
            annotator_id=payload.annotator_id,
            accepted=len(payload.annotations),
            message="Annotations saved",
        )

    async def get_agreement(self, conversation_id: str) -> AgreementResponse | None:
        record = await self._repo.get_agreement(conversation_id)
        if not record:
            return None
        return AgreementResponse(
            conversation_id=conversation_id,
            cohen_kappa=record.cohen_kappa,
            agreement_level=kappa_to_level(record.cohen_kappa),
            routing_decision=record.routing_decision,
            annotator_count=record.annotator_count,
            label_distribution=record.label_distribution,
        )

    async def recompute_agreement(self, conversation_id: str) -> None:
        from collections import Counter
        all_records = await self._repo.get_annotations_for_conversation(conversation_id)
        if len(all_records) < 2:
            return

        all_annotations = [ann for record in all_records for ann in record.annotations]
        all_labels = [ann["label"] for ann in all_annotations]
        distribution = dict(Counter(all_labels))

        confidences = [ann.get("confidence", 1.0) for ann in all_annotations]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0

        if len(all_records) == 2:
            labels_a = [a["label"] for a in all_records[0].annotations]
            labels_b = [a["label"] for a in all_records[1].annotations]
            kappa = cohen_kappa(labels_a, labels_b)
        else:
            kappa = None

        decision = routing_decision(kappa, self._settings.annotation_auto_label_threshold, avg_confidence)

        agreement = AgreementRecord(
            id=f"agr_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            cohen_kappa=kappa,
            annotator_count=len(all_records),
            routing_decision=decision,
            label_distribution=distribution,
        )
        await self._repo.save_agreement(agreement)
