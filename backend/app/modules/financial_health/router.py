from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.financial_health.service import FinancialHealthService

router = APIRouter(prefix="/financial-health", tags=["financial_health"])


class ScoreOut(BaseModel):
    score: int
    factors: dict


@router.get("/score", response_model=ScoreOut)
async def get_score(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScoreOut:
    service = FinancialHealthService(session)
    result = await service.compute(user_id)
    await session.commit()
    return ScoreOut(score=result.score, factors=result.factors)
