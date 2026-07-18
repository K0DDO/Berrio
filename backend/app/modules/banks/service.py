from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.banks.models import BankConnection, Transaction
from app.modules.banks.parsers import get_parser


class BankConnectionCreate(BaseModel):
    bank_code: str = Field(min_length=2, max_length=32)
    label: str | None = None


class BankConnectionOut(BaseModel):
    id: UUID
    bank_code: str
    status: str
    label: str | None
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


class ParseEmailRequest(BaseModel):
    bank_code: str
    subject: str = ""
    body: str


class TransactionOut(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    merchant_raw: str
    booked_at: datetime
    source: str
    external_id: str

    model_config = {"from_attributes": True}


class BankService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_connection(self, user_id: UUID, data: BankConnectionCreate) -> BankConnection:
        code = data.bank_code.lower()
        try:
            get_parser(code)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        row = BankConnection(user_id=user_id, bank_code=code, label=data.label, status="active")
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_connections(self, user_id: UUID) -> list[BankConnection]:
        result = await self._session.execute(
            select(BankConnection).where(BankConnection.user_id == user_id)
        )
        return list(result.scalars().all())

    async def ingest_email(
        self, user_id: UUID, data: ParseEmailRequest
    ) -> list[Transaction]:
        parser = get_parser(data.bank_code)
        parsed = parser.parse(data.subject, data.body)
        saved: list[Transaction] = []
        for tx in parsed:
            existing = await self._session.execute(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.external_id == tx.external_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            row = Transaction(
                user_id=user_id,
                source="BANK",
                amount=tx.amount,
                currency=tx.currency,
                merchant_raw=tx.merchant_raw,
                booked_at=tx.booked_at,
                external_id=tx.external_id,
                status="posted",
            )
            self._session.add(row)
            saved.append(row)
        await self._session.flush()
        return saved

    async def list_transactions(self, user_id: UUID) -> list[Transaction]:
        result = await self._session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.booked_at.desc())
        )
        return list(result.scalars().all())
