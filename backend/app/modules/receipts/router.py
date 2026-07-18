from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.families.permission_checker import (
    FamilyPermissionChecker,
    FamilyPermissionKey,
)
from app.modules.receipts.schemas import ReceiptListOut, ReceiptOut, ReceiptScanRequest
from app.modules.receipts.service import ReceiptService

router = APIRouter(prefix="/receipts", tags=["receipts"])


def get_receipt_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReceiptService:
    return ReceiptService(session)


@router.post("/scan", response_model=ReceiptOut, status_code=201)
async def scan_receipt(
    body: ReceiptScanRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
) -> ReceiptOut:
    """Accept QR fiscal params only — never upload receipt photos."""
    return await service.scan(user_id, body)


@router.get("", response_model=ReceiptListOut)
async def list_receipts(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    family_id: Annotated[UUID | None, Query()] = None,
) -> ReceiptListOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.RECEIPTS,
    )
    items, total = await service.list(user_id, limit=limit, offset=offset, scope_user_ids=scope)
    return ReceiptListOut(items=items, total=total)


@router.get("/{receipt_id}", response_model=ReceiptOut)
async def get_receipt(
    receipt_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[ReceiptService, Depends(get_receipt_service)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> ReceiptOut:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.RECEIPTS,
    )
    return await service.get(user_id, receipt_id, scope_user_ids=scope)
