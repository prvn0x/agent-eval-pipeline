from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.suggestion import SuggestionsResponse
from app.services.self_updater_service import SelfUpdaterService

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


class TriggerRequest(BaseModel):
    agent_version: str


class TriggerResponse(BaseModel):
    agent_version: str
    suggestions_saved: int


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_self_updater(
    payload: TriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> TriggerResponse:
    saved = await SelfUpdaterService(db).run(payload.agent_version)
    await db.commit()
    return TriggerResponse(agent_version=payload.agent_version, suggestions_saved=saved)


@router.get("", response_model=SuggestionsResponse)
async def list_suggestions(
    agent_version: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> SuggestionsResponse:
    return await SelfUpdaterService(db).list_suggestions(agent_version)
