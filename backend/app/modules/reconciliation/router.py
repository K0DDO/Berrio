from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.reconciliation.schemas import ReconciliationMatchOut, ReconciliationRunResult
from app.modules.reconciliation.service import ReconciliationService

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.post("/run", response_model=ReconciliationRunResult)
async def run_reconciliation(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReconciliationRunResult:
    """Score unmatched receipts against bank transactions and create suggestions."""
    result = await ReconciliationService(session).run(user_id)
    await session.commit()
    return result


@router.get("/suggestions", response_model=list[ReconciliationMatchOut])
async def list_suggestions(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: Annotated[str | None, Query()] = "SUGGESTED",
) -> list[ReconciliationMatchOut]:
    return await ReconciliationService(session).list_suggestions(user_id, status=status)


@router.post("/{match_id}/confirm", response_model=ReconciliationMatchOut)
async def confirm_match(
    match_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReconciliationMatchOut:
    result = await ReconciliationService(session).confirm(user_id, match_id)
    await session.commit()
    return result


@router.post("/{match_id}/reject", response_model=ReconciliationMatchOut)
async def reject_match(
    match_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReconciliationMatchOut:
    result = await ReconciliationService(session).reject(user_id, match_id)
    await session.commit()
    return result
