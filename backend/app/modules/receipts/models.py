from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class ReceiptStatus(StrEnum):
    PENDING = "pending"
    FETCHING = "fetching"
    DONE = "done"
    FAILED = "failed"
    NEEDS_CONFIRMATION = "needs_confirmation"


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("user_id", "fn", "fd", "fp", name="uq_receipts_user_fn_fd_fp"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    fn: Mapped[str] = mapped_column(String(64), nullable=False)
    fd: Mapped[str] = mapped_column(String(64), nullable=False)
    fp: Mapped[str] = mapped_column(String(64), nullable=False)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    store_inn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ReceiptStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recognition_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["ReceiptItem"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name_raw: Mapped[str] = mapped_column(String(512), nullable=False)
    name_display: Mapped[str | None] = mapped_column(String(512), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("1"))
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    sum: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    product_variant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    receipt: Mapped[Receipt] = relationship(back_populates="items")
