from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.conversation import (
    BatchIngestRequest,
    BatchIngestResponse,
    ConversationCreate,
    ConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=ConversationResponse)
async def ingest_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    return await ConversationService(db).ingest(payload)


@router.post(
    "/batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BatchIngestResponse,
)
async def ingest_batch(
    payload: BatchIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchIngestResponse:
    return await ConversationService(db).ingest_batch(payload)
