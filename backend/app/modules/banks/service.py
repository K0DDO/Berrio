from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.banks.models import BankConnection, Transaction
from app.modules.banks.parsers import get_parser
from app.modules.banks.statement_parsers import parse_statement_file
from app.modules.reconciliation.service import ReconciliationService


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
    connection_id: UUID | None = None


class TransactionOut(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    merchant_raw: str
    booked_at: datetime
    source: str
    external_id: str
    bank_connection_id: UUID | None = None

    model_config = {"from_attributes": True}


class StatementUploadOut(BaseModel):
    imported: int
    skipped_duplicates: int
    messages: list[str]
    reconciliation_created: int = 0


class BankService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_connection(self, user_id: UUID, data: BankConnectionCreate) -> BankConnection:
        code = self._normalize_bank_code(data.bank_code)
        if code not in {"other", "sber", "tinkoff", "alfa", "vtb"}:
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

    async def ingest_email(self, user_id: UUID, data: ParseEmailRequest) -> list[Transaction]:

        parser = get_parser(data.bank_code)
        connection_id = data.connection_id
        if connection_id is not None:
            conn = await self._session.get(BankConnection, connection_id)
            if conn is None or conn.user_id != user_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found")
        else:
            result = await self._session.execute(
                select(BankConnection).where(
                    BankConnection.user_id == user_id,
                    BankConnection.bank_code == data.bank_code.lower(),
                )
            )
            conn = result.scalars().first()
            connection_id = conn.id if conn else None

        try:
            parsed = parser.parse(data.subject, data.body)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parser failed: {exc}",
            ) from exc

        if not parsed:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No transactions recognized in email body",
            )

        return await self._persist_txs(
            user_id=user_id, parsed=parsed, connection_id=connection_id, source="BANK"
        )

    async def ingest_statement(
        self,
        user_id: UUID,
        *,
        bank_code: str,
        filename: str,
        content: bytes,
    ) -> StatementUploadOut:
        from datetime import UTC, datetime

        code = self._normalize_bank_code(bank_code)
        try:
            parsed = parse_statement_file(filename=filename, content=content, bank_code=code)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        if not parsed:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Не удалось распознать операции в файле",
            )

        result = await self._session.execute(
            select(BankConnection).where(
                BankConnection.user_id == user_id,
                BankConnection.bank_code == code,
            )
        )
        conn = result.scalars().first()
        if conn is None:
            conn = BankConnection(user_id=user_id, bank_code=code, label=code, status="active")
            self._session.add(conn)
            await self._session.flush()

        saved = await self._persist_txs(
            user_id=user_id,
            parsed=parsed,
            connection_id=conn.id,
            source="STATEMENT",
        )
        imported = len(saved)
        skipped = max(0, len(parsed) - imported)

        messages: list[str] = [f"Импортировано операций: {imported}"]
        if skipped:
            messages.append(f"Пропущено дублей: {skipped}")

        recon = ReconciliationService(self._session)
        run = await recon.run(user_id)
        for _ in run.suggestions[:10]:
            messages.append("Найдено совпадение с чеком Berrio — проверьте сверку")
        if run.created == 0 and imported:
            messages.append("Найдены новые операции без совпадения с чеками Berrio")

        conn.last_synced_at = datetime.now(UTC)
        await self._session.flush()
        return StatementUploadOut(
            imported=imported,
            skipped_duplicates=skipped,
            messages=messages,
            reconciliation_created=run.created,
        )

    async def _persist_txs(
        self,
        *,
        user_id: UUID,
        parsed: list,
        connection_id: UUID | None,
        source: str,
    ) -> list[Transaction]:
        from datetime import UTC, datetime

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
                source=source,
                amount=tx.amount,
                currency=tx.currency,
                merchant_raw=tx.merchant_raw,
                booked_at=tx.booked_at,
                external_id=tx.external_id,
                bank_connection_id=connection_id,
                status="posted",
            )
            self._session.add(row)
            saved.append(row)

        if connection_id is not None:
            conn = await self._session.get(BankConnection, connection_id)
            if conn is not None:
                conn.last_synced_at = datetime.now(UTC)

        await self._session.flush()
        return saved

    @staticmethod
    def _normalize_bank_code(code: str) -> str:
        c = code.lower().strip()
        aliases = {
            "t-bank": "tinkoff",
            "tbank": "tinkoff",
            "тинькофф": "tinkoff",
            "сбер": "sber",
            "sberbank": "sber",
            "альфа": "alfa",
            "alfabank": "alfa",
            "втб": "vtb",
            "другой": "other",
        }
        return aliases.get(c, c)

    async def list_transactions(self, user_id: UUID) -> list[Transaction]:
        return await self.list_transactions_for_users([user_id])

    async def list_transactions_for_users(self, user_ids: list[UUID]) -> list[Transaction]:
        result = await self._session.execute(
            select(Transaction)
            .where(Transaction.user_id.in_(user_ids))
            .order_by(Transaction.booked_at.desc())
        )
        return list(result.scalars().all())
