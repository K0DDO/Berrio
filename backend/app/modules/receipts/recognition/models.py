"""Confidence-bearing receipt recognition models."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ConfidenceField[T](BaseModel):
    value: T | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RecognizedItem(BaseModel):
    name: str
    qty: Decimal = Decimal("1")
    price: Decimal | None = None
    sum: Decimal | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    name_display: str | None = None
    brand: str | None = None
    volume_label: str | None = None
    weight_label: str | None = None
    category_slug: str | None = None


class StructuredReceipt(BaseModel):
    """Result of OCR → structure analysis (before persistence)."""

    merchant: ConfidenceField[str] = Field(default_factory=ConfidenceField)
    amount: ConfidenceField[Decimal] = Field(default_factory=ConfidenceField)
    purchased_at: ConfidenceField[str] = Field(default_factory=ConfidenceField)
    items: list[RecognizedItem] = Field(default_factory=list)
    category_hint: ConfidenceField[str] = Field(default_factory=ConfidenceField)
    raw_ocr_text: str = ""
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_confirmation: bool = True
    success: bool = False
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)

    def to_meta_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    requires_confirmation: bool
    reasons: list[str] = field(default_factory=list)
    status: str = "needs_confirmation"  # done | needs_confirmation | failed


class AnalyzeTextRequest(BaseModel):
    """Client-side OCR / pasted receipt text — photos are not stored."""

    raw_text: str = Field(min_length=1, max_length=20000)
    fn: str | None = Field(default=None, max_length=64)
    fd: str | None = Field(default=None, max_length=64)
    fp: str | None = Field(default=None, max_length=64)
    persist: bool = True


class AnalyzeTextResponse(BaseModel):
    success: bool
    requires_confirmation: bool
    reason: str | None = None
    structured: StructuredReceipt
    receipt_id: str | None = None
    status: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ReceiptConfirmRequest(BaseModel):
    store_name: str | None = Field(default=None, max_length=255)
    total_amount: Decimal | None = None
    purchased_at: str | None = None
    category_slug: str | None = None
    items: list[RecognizedItem] = Field(default_factory=list)
    confirm_as_is: bool = False
    save_as_draft: bool = False
    date_ignored: bool = False
    date_confirmed: bool = False
