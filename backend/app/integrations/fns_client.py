"""FNS receipt lookup — stub by default; real HTTP when FNS_API_TOKEN is set."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class FnsLineItem:
    name: str
    qty: Decimal
    price: Decimal
    sum: Decimal


@dataclass(frozen=True, slots=True)
class FnsReceiptData:
    store_name: str
    store_inn: str | None
    purchased_at: datetime
    total_amount: Decimal
    items: list[FnsLineItem]


class FnsClient:
    """Abstract FNS / OFD receipt checker."""

    async def fetch(
        self,
        *,
        fn: str,
        fd: str,
        fp: str,
        purchased_at: datetime | None = None,
        total_amount: Decimal | None = None,
    ) -> FnsReceiptData:
        raise NotImplementedError


class StubFnsClient(FnsClient):
    async def fetch(
        self,
        *,
        fn: str,
        fd: str,
        fp: str,
        purchased_at: datetime | None = None,
        total_amount: Decimal | None = None,
    ) -> FnsReceiptData:
        when = purchased_at or datetime.now(UTC)
        total = total_amount if total_amount is not None else Decimal("249.90")
        milk = (total * Decimal("0.4")).quantize(Decimal("0.01"))
        bread = (total - milk).quantize(Decimal("0.01"))
        return FnsReceiptData(
            store_name="Пятёрочка",
            store_inn="7728029110",
            purchased_at=when,
            total_amount=total,
            items=[
                FnsLineItem(
                    name="Молоко Простоквашино 2.5%",
                    qty=Decimal("1"),
                    price=milk,
                    sum=milk,
                ),
                FnsLineItem(
                    name="Хлеб Бородинский",
                    qty=Decimal("1"),
                    price=bread,
                    sum=bread,
                ),
            ],
        )


class ProverkaChekaFnsClient(FnsClient):
    """
    Real provider via proverkacheka.com partner API.

    Requires FNS_API_TOKEN. Falls through is handled by factory.
    Docs: POST /api/v1/check/get with token + qrraw or fn/fd/fp/s/t/n.
    """

    def __init__(
        self,
        *,
        token: str,
        base_url: str = "https://proverkacheka.com/api/v1/check/get",
        timeout: float = 30.0,
    ) -> None:
        self._token = token
        self._url = base_url
        self._timeout = timeout

    async def fetch(
        self,
        *,
        fn: str,
        fd: str,
        fp: str,
        purchased_at: datetime | None = None,
        total_amount: Decimal | None = None,
    ) -> FnsReceiptData:
        qrraw = self._build_qrraw(
            fn=fn, fd=fd, fp=fp, purchased_at=purchased_at, total_amount=total_amount
        )
        # Form-style payload — some plans also accept qrraw alongside discrete fields
        form = {
            "token": self._token,
            "fn": fn,
            "fd": fd,
            "fp": fp,
            "n": "1",
            "qr": "0",
        }
        if total_amount is not None:
            form["s"] = f"{total_amount:.2f}"
        if purchased_at is not None:
            form["t"] = purchased_at.strftime("%Y%m%dT%H%M")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._url, data={**form, "qrraw": qrraw})
            response.raise_for_status()
            body: dict[str, Any] = response.json()

        logger.info("fns.fetch", code=body.get("code"), fn=fn, fd=fd)
        if body.get("code") not in (1, "1", True):
            detail = body.get("data") or body.get("message") or body
            raise RuntimeError(f"FNS provider rejected receipt: {detail}")

        raw = body.get("data") or {}
        ticket = raw.get("json") if isinstance(raw, dict) else None
        if not isinstance(ticket, dict):
            ticket = raw if isinstance(raw, dict) else {}
        return self._parse_ticket(
            ticket,
            fallback_when=purchased_at,
            fallback_total=total_amount,
        )

    @staticmethod
    def _build_qrraw(
        *,
        fn: str,
        fd: str,
        fp: str,
        purchased_at: datetime | None,
        total_amount: Decimal | None,
    ) -> str:
        parts = [f"fn={fn}", f"i={fd}", f"fp={fp}", "n=1"]
        if purchased_at is not None:
            parts.insert(0, f"t={purchased_at.strftime('%Y%m%dT%H%M')}")
        if total_amount is not None:
            parts.insert(1 if purchased_at else 0, f"s={total_amount:.2f}")
        return "&".join(parts)

    def _parse_ticket(
        self,
        ticket: dict[str, Any],
        *,
        fallback_when: datetime | None,
        fallback_total: Decimal | None,
    ) -> FnsReceiptData:
        store = (
            ticket.get("user")
            or ticket.get("retailPlace")
            or ticket.get("store_name")
            or "Unknown store"
        )
        inn = ticket.get("userInn") or ticket.get("store_inn")
        when = self._parse_dt(ticket.get("dateTime") or ticket.get("date_time")) or (
            fallback_when or datetime.now(UTC)
        )
        total_raw = (
            ticket.get("totalSum")
            if ticket.get("totalSum") is not None
            else ticket.get("total_amount")
        )
        total = self._money(total_raw)
        if total is None:
            total = fallback_total or Decimal("0")
        else:
            total = self._normalize_money_field(total)

        items: list[FnsLineItem] = []
        for row in ticket.get("items") or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or row.get("productName") or "Item")
            qty = Decimal(str(row.get("quantity") or row.get("qty") or 1))
            price_raw = self._money(row.get("price")) or Decimal("0")
            sum_raw = self._money(row.get("sum"))
            price = self._normalize_money_field(price_raw)
            if sum_raw is not None:
                line_sum = self._normalize_money_field(sum_raw)
            else:
                line_sum = (price * qty).quantize(Decimal("0.01"))
            items.append(FnsLineItem(name=name, qty=qty, price=price, sum=line_sum))

        if not items and total > 0:
            items = [FnsLineItem(name="Purchase", qty=Decimal("1"), price=total, sum=total)]

        return FnsReceiptData(
            store_name=str(store)[:255],
            store_inn=str(inn)[:32] if inn else None,
            purchased_at=when if when.tzinfo else when.replace(tzinfo=UTC),
            total_amount=total.quantize(Decimal("0.01")),
            items=items,
        )

    @staticmethod
    def _normalize_money_field(value: Decimal) -> Decimal:
        """FNS partner payloads often express money in kopecks as integers."""
        if value == value.to_integral_value() and value >= Decimal("100"):
            return (value / Decimal("100")).quantize(Decimal("0.01"))
        return value.quantize(Decimal("0.01"))

    @staticmethod
    def _money(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        text = str(value).replace(" ", "T")
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(text[:19], fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None


def get_fns_client() -> FnsClient:
    settings = get_settings()
    token = (settings.fns_api_token or "").strip()
    provider = (settings.fns_provider or "auto").lower()
    if provider == "stub" or not token:
        if provider != "stub" and not token:
            logger.debug("fns.using_stub", reason="FNS_API_TOKEN not set")
        return StubFnsClient()
    return ProverkaChekaFnsClient(
        token=token,
        base_url=settings.fns_api_url,
    )
