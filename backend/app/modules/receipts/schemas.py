from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ReceiptScanRequest(BaseModel):
    """QR fiscal parameters — photos are never accepted or stored."""

    fn: str = Field(min_length=1, max_length=64)
    fd: str = Field(min_length=1, max_length=64)
    fp: str = Field(min_length=1, max_length=64)
    purchased_at: datetime | None = None
    total_amount: Decimal | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)


class ReceiptItemOut(BaseModel):
    id: UUID
    name_raw: str
    qty: Decimal
    price: Decimal
    sum: Decimal
    category_id: UUID | None = None
    category_name: str | None = None
    product_variant_id: UUID | None = None
    previous_price: Decimal | None = None
    price_change_pct: float | None = None

    model_config = {"from_attributes": True}


class ReceiptOut(BaseModel):
    id: UUID
    fn: str
    fd: str
    fp: str
    status: str
    purchased_at: datetime | None
    total_amount: Decimal | None
    store_name: str | None
    store_inn: str | None
    error_message: str | None = None
    items: list[ReceiptItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ReceiptListOut(BaseModel):
    items: list[ReceiptOut]
    total: int
