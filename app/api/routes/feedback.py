from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.feedback import AgreementResponse, FeedbackResponse, FeedbackSubmit
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/{conversation_id}", status_code=status.HTTP_201_CREATED, response_model=FeedbackResponse)
async def submit_feedback(
    conversation_id: str,
    payload: FeedbackSubmit,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    return await FeedbackService(db).submit(conversation_id, payload)


@router.get("/agreement/{conversation_id}", response_model=AgreementResponse)
async def get_agreement(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> AgreementResponse:
    result = await FeedbackService(db).get_agreement(conversation_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No annotations found for '{conversation_id}'",
        )
    return result
