from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.banks.service import (
    BankConnectionCreate,
    BankConnectionOut,
    BankService,
    ParseEmailRequest,
    TransactionOut,
)
from app.modules.families.permission_checker import (
    FamilyPermissionChecker,
    FamilyPermissionKey,
)

router = APIRouter(prefix="/banks", tags=["banks"])


@router.post("/connections", response_model=BankConnectionOut, status_code=201)
async def create_connection(
    body: BankConnectionCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BankConnectionOut:
    service = BankService(session)
    row = await service.create_connection(user_id, body)
    await session.commit()
    return BankConnectionOut.model_validate(row)


@router.get("/connections", response_model=list[BankConnectionOut])
async def list_connections(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BankConnectionOut]:
    service = BankService(session)
    rows = await service.list_connections(user_id)
    return [BankConnectionOut.model_validate(r) for r in rows]


@router.post("/parse-email", response_model=list[TransactionOut])
async def parse_email(
    body: ParseEmailRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TransactionOut]:
    """Ingest a forwarded bank email body without IMAP (IMAP wiring later)."""
    service = BankService(session)
    rows = await service.ingest_email(user_id, body)
    await session.commit()
    return [TransactionOut.model_validate(r) for r in rows]


@router.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    family_id: Annotated[UUID | None, Query()] = None,
) -> list[TransactionOut]:
    checker = FamilyPermissionChecker(session)
    scope = await checker.resolve_scope(
        actor_id=user_id,
        family_id=family_id,
        permission=FamilyPermissionKey.TRANSACTIONS,
    )
    service = BankService(session)
    rows = await service.list_transactions_for_users(scope)
    return [TransactionOut.model_validate(r) for r in rows]
