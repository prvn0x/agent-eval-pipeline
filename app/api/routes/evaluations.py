from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.evaluation import (
    EvaluationResponse,
    EvaluationScores,
    IssueDetected,
    ImprovementSuggestion,
    ToolEvaluation,
)
from app.services.evaluation_query_service import EvaluationQueryService

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.get("/{conversation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    evaluation = await EvaluationQueryService(db).get_by_conversation(conversation_id)

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation for '{conversation_id}' not found — may still be processing",
        )

    return EvaluationResponse(
        evaluation_id=evaluation.id,
        conversation_id=evaluation.conversation_id,
        status="COMPLETED",
        scores=EvaluationScores(
            overall=evaluation.overall_score or 0.0,
            response_quality=evaluation.response_quality,
            tool_accuracy=evaluation.tool_accuracy,
            coherence=evaluation.coherence,
        ),
        tool_evaluation=(
            ToolEvaluation(**evaluation.tool_evaluation)
            if evaluation.tool_evaluation else None
        ),
        issues_detected=[IssueDetected(**i) for i in (evaluation.issues_detected or [])],
        improvement_suggestions=[
            ImprovementSuggestion(**s) for s in (evaluation.improvement_suggestions or [])
        ],
        created_at=evaluation.created_at,
    )
