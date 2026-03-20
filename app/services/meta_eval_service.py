import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.evaluation import Evaluation
from app.db.models.feedback import AnnotationRecord, AgreementRecord
from app.db.models.meta_eval import MetaEvalReport
from app.db.repositories.meta_eval_repository import MetaEvalRepository
from app.domain.meta_eval.calibrator import calibrate
from app.schemas.meta_eval import BlindSpot, EvaluatorCalibration, MetaEvalResponse


class MetaEvalService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MetaEvalRepository(session)

    async def run(self) -> MetaEvalResponse:
        conversations = await self._collect()
        result = calibrate(conversations)

        report = MetaEvalReport(
            id=f"meta_{uuid.uuid4().hex[:8]}",
            conversations_analyzed=result.conversations_analyzed,
            overall_agreement=result.overall_agreement,
            evaluator_calibration=result.evaluator_calibration,
            blind_spots=result.blind_spots,
        )
        await self._repo.save(report)
        return self._to_response(report)

    async def get_latest(self) -> MetaEvalResponse | None:
        report = await self._repo.get_latest()
        if not report:
            return None
        return self._to_response(report)

    async def _collect(self) -> list[dict]:
        agreement_rows = await self._session.execute(
            select(AgreementRecord).order_by(AgreementRecord.created_at.desc())
        )
        # latest agreement per conversation
        agreements: dict[str, AgreementRecord] = {}
        for row in agreement_rows.scalars().all():
            if row.conversation_id not in agreements:
                agreements[row.conversation_id] = row

        if not agreements:
            return []

        conv_ids = list(agreements.keys())

        eval_rows = await self._session.execute(
            select(Evaluation).where(Evaluation.conversation_id.in_(conv_ids))
        )
        evaluations: dict[str, Evaluation] = {
            ev.conversation_id: ev for ev in eval_rows.scalars().all()
        }

        annotation_rows = await self._session.execute(
            select(AnnotationRecord).where(AnnotationRecord.conversation_id.in_(conv_ids))
        )
        annotation_types: dict[str, list[str]] = {}
        for ann in annotation_rows.scalars().all():
            cid = ann.conversation_id
            annotation_types.setdefault(cid, [])
            for item in (ann.annotations or []):
                if item.get("type"):
                    annotation_types[cid].append(item["type"])

        conv_rows = await self._session.execute(
            select(Conversation).where(Conversation.id.in_(conv_ids))
        )
        user_ratings: dict[str, int | None] = {
            c.id: (c.feedback or {}).get("user_rating")
            for c in conv_rows.scalars().all()
        }

        return [
            {
                "evaluation": evaluations[cid],
                "agreement": agreement,
                "annotation_types": annotation_types.get(cid, []),
                "user_rating": user_ratings.get(cid),
            }
            for cid, agreement in agreements.items()
            if cid in evaluations
        ]

    def _to_response(self, report: MetaEvalReport) -> MetaEvalResponse:
        return MetaEvalResponse(
            conversations_analyzed=report.conversations_analyzed,
            overall_agreement=report.overall_agreement,
            evaluator_calibration=[
                EvaluatorCalibration(**item) for item in report.evaluator_calibration
            ],
            blind_spots=[BlindSpot(**item) for item in report.blind_spots],
            run_at=report.created_at,
        )
