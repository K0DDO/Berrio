from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.receipts.models import Receipt, ReceiptItem, ReceiptStatus


class ReceiptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, receipt_id: UUID, user_id: UUID) -> Receipt | None:
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(Receipt.id == receipt_id, Receipt.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_fingerprint(
        self, *, user_id: UUID, fn: str, fd: str, fp: str
    ) -> Receipt | None:
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(
                Receipt.user_id == user_id,
                Receipt.fn == fn,
                Receipt.fd == fd,
                Receipt.fp == fp,
            )
        )
        return result.scalar_one_or_none()

    async def create_pending(
        self,
        *,
        user_id: UUID,
        fn: str,
        fd: str,
        fp: str,
        purchased_at: datetime | None,
        total_amount: Decimal | None,
    ) -> Receipt:
        receipt = Receipt(
            user_id=user_id,
            fn=fn,
            fd=fd,
            fp=fp,
            purchased_at=purchased_at,
            total_amount=total_amount,
            status=ReceiptStatus.PENDING,
        )
        self._session.add(receipt)
        await self._session.flush()
        return receipt

    async def list_for_user(self, user_id: UUID, *, limit: int = 50, offset: int = 0) -> tuple[list[Receipt], int]:
        total = await self._session.scalar(
            select(func.count()).select_from(Receipt).where(Receipt.user_id == user_id)
        )
        result = await self._session.execute(
            select(Receipt)
            .options(selectinload(Receipt.items))
            .where(Receipt.user_id == user_id)
            .order_by(Receipt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def add_item(self, item: ReceiptItem) -> ReceiptItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def save(self, receipt: Receipt) -> Receipt:
        await self._session.flush()
        return receipt
