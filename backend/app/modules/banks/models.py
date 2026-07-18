from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    # email/imap encrypted later — Stage 7 stores placeholder only
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_transactions_user_external"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="BANK")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    merchant_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    merchant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    bank_connection_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="posted")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
