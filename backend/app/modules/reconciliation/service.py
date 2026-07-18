from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.banks.models import Transaction
from app.modules.receipts.models import Receipt, ReceiptStatus
from app.modules.reconciliation.engine import ReconciliationEngine
from app.modules.reconciliation.models import MatchStatus, ReconciliationMatch
from app.modules.reconciliation.schemas import ReconciliationMatchOut, ReconciliationRunResult


class ReconciliationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._engine = ReconciliationEngine()
        self._audit = AuditService(session)

    async def run(self, user_id: UUID) -> ReconciliationRunResult:
        receipts = await self._unmatched_receipts(user_id)
        txs = await self._unmatched_transactions(user_id)
        locked = await self._locked_ids(user_id)

        candidates = self._engine.suggest(
            receipts,
            txs,
            used_receipts=locked["receipts"],
            used_txs=locked["transactions"],
        )

        created: list[ReconciliationMatch] = []
        for c in candidates:
            existing = await self._session.execute(
                select(ReconciliationMatch).where(
                    ReconciliationMatch.receipt_id == c.receipt_id,
                    ReconciliationMatch.transaction_id == c.transaction_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            row = ReconciliationMatch(
                user_id=user_id,
                receipt_id=c.receipt_id,
                transaction_id=c.transaction_id,
                score=c.score,
                status=MatchStatus.SUGGESTED,
                reasons=c.reasons,
            )
            self._session.add(row)
            created.append(row)

        await self._session.flush()
        await self._audit.record(
            action="reconciliation.run",
            actor_user_id=user_id,
            entity_type="reconciliation",
            metadata={"created": len(created)},
        )
        return ReconciliationRunResult(
            created=len(created),
            suggestions=[ReconciliationMatchOut.model_validate(r) for r in created],
        )

    async def list_suggestions(
        self, user_id: UUID, *, status: str | None = MatchStatus.SUGGESTED
    ) -> list[ReconciliationMatchOut]:
        stmt = select(ReconciliationMatch).where(ReconciliationMatch.user_id == user_id)
        if status:
            stmt = stmt.where(ReconciliationMatch.status == status)
        stmt = stmt.order_by(ReconciliationMatch.score.desc())
        result = await self._session.execute(stmt)
        return [ReconciliationMatchOut.model_validate(r) for r in result.scalars().all()]

    async def confirm(self, user_id: UUID, match_id: UUID) -> ReconciliationMatchOut:
        row = await self._get(user_id, match_id)
        if row.status == MatchStatus.REJECTED:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Match was rejected")
        row.status = MatchStatus.CONFIRMED
        row.decided_at = datetime.now(UTC)
        await self._session.flush()
        await self._audit.record(
            action="reconciliation.confirm",
            actor_user_id=user_id,
            entity_type="reconciliation_match",
            entity_id=row.id,
        )
        return ReconciliationMatchOut.model_validate(row)

    async def reject(self, user_id: UUID, match_id: UUID) -> ReconciliationMatchOut:
        row = await self._get(user_id, match_id)
        if row.status == MatchStatus.CONFIRMED:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Match was confirmed")
        row.status = MatchStatus.REJECTED
        row.decided_at = datetime.now(UTC)
        await self._session.flush()
        await self._audit.record(
            action="reconciliation.reject",
            actor_user_id=user_id,
            entity_type="reconciliation_match",
            entity_id=row.id,
        )
        return ReconciliationMatchOut.model_validate(row)

    async def _get(self, user_id: UUID, match_id: UUID) -> ReconciliationMatch:
        result = await self._session.execute(
            select(ReconciliationMatch).where(
                ReconciliationMatch.id == match_id,
                ReconciliationMatch.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Match not found")
        return row

    async def _unmatched_receipts(self, user_id: UUID) -> list[Receipt]:
        confirmed = select(ReconciliationMatch.receipt_id).where(
            ReconciliationMatch.user_id == user_id,
            ReconciliationMatch.status == MatchStatus.CONFIRMED,
        )
        result = await self._session.execute(
            select(Receipt).where(
                Receipt.user_id == user_id,
                Receipt.status == ReceiptStatus.DONE,
                Receipt.id.not_in(confirmed),
            )
        )
        return list(result.scalars().all())

    async def _unmatched_transactions(self, user_id: UUID) -> list[Transaction]:
        confirmed = select(ReconciliationMatch.transaction_id).where(
            ReconciliationMatch.user_id == user_id,
            ReconciliationMatch.status == MatchStatus.CONFIRMED,
        )
        result = await self._session.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.id.not_in(confirmed),
            )
        )
        return list(result.scalars().all())

    async def _locked_ids(self, user_id: UUID) -> dict[str, set]:
        result = await self._session.execute(
            select(ReconciliationMatch).where(
                ReconciliationMatch.user_id == user_id,
                ReconciliationMatch.status.in_([MatchStatus.CONFIRMED, MatchStatus.SUGGESTED]),
            )
        )
        receipts: set = set()
        txs: set = set()
        for row in result.scalars().all():
            receipts.add(row.receipt_id)
            txs.add(row.transaction_id)
        return {"receipts": receipts, "transactions": txs}
