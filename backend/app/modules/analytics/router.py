from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.analytics.service import AnalyticsService, AnalyticsSummaryOut
from app.modules.auth.dependencies import get_current_user_id

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryOut)
async def analytics_summary(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[str, Query()] = "month",
) -> AnalyticsSummaryOut:
    service = AnalyticsService(session)
    summary = await service.summary(user_id, period=period)
    await session.commit()
    return summary
