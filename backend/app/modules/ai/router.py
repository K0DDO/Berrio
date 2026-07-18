from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.ai.service import AiChatRequest, AiChatResponse, AiInsightOut, AiService
from app.modules.auth.dependencies import get_current_user_id
from app.modules.families.permission_checker import FamilyPermissionChecker, FamilyPermissionKey

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=AiChatResponse)
async def ai_chat(
    body: AiChatRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> AiChatResponse:
    checker = FamilyPermissionChecker(session)
    await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.AI_INSIGHTS,
    )
    service = AiService(session)
    result = await service.chat(user_id, body)
    await session.commit()
    return result


@router.get("/insights", response_model=list[AiInsightOut])
async def ai_insights(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    period: Annotated[str, Query()] = "month",
    family_id: Annotated[UUID | None, Query()] = None,
) -> list[AiInsightOut]:
    checker = FamilyPermissionChecker(session)
    await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.AI_INSIGHTS,
    )
    service = AiService(session)
    result = await service.insights(user_id, period=period)
    await session.commit()
    return result
