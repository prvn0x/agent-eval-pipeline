from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.meta_eval import MetaEvalResponse
from app.services.meta_eval_service import MetaEvalService

router = APIRouter(prefix="/meta-eval", tags=["Meta Evaluation"])


@router.post("/run", response_model=MetaEvalResponse, status_code=status.HTTP_201_CREATED)
async def run_meta_eval(
    db: AsyncSession = Depends(get_db),
) -> MetaEvalResponse:
    service = MetaEvalService(db)
    result = await service.run()
    await db.commit()
    return result


@router.get("/latest", response_model=MetaEvalResponse)
async def get_latest_meta_eval(
    db: AsyncSession = Depends(get_db),
) -> MetaEvalResponse:
    result = await MetaEvalService(db).get_latest()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No meta-eval report found. Run POST /meta-eval/run first.",
        )
    return result
