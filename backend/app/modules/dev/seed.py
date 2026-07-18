"""Development-only demo seed — user, receipts, goals, AI insights."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_email
from app.modules.ai.service import AiService
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.service import AuthService
from app.modules.budgets.schemas import BudgetCreate
from app.modules.budgets.service import BudgetService
from app.modules.goals.schemas import GoalCreate
from app.modules.goals.service import GoalService
from app.modules.receipts.recognition.models import AnalyzeTextRequest, RecognizedItem
from app.modules.receipts.schemas import ReceiptConfirmRequest, ReceiptScanRequest
from app.modules.receipts.service import ReceiptService

logger = structlog.get_logger(__name__)

DEMO_EMAIL = "demo@berrio.app"
DEMO_PASSWORD = "Demo1234!"
DEMO_NAME = "Demo User"
DEMO_DEVICE = "local-beta-seed"


async def seed_demo_data(session: AsyncSession) -> dict[str, object]:
    """
    Idempotent demo dataset for local beta.

    Raises RuntimeError if called outside development / debug.
    """
    settings = get_settings()
    if settings.app_env == "production" or not settings.debug:
        raise RuntimeError(
            "Demo seed is only allowed in development (DEBUG=true, APP_ENV!=production)"
        )

    auth = AuthService(session)
    repo = AuthRepository(session)
    existing = await repo.get_user_by_email_hash(hash_email(DEMO_EMAIL))
    created_user = False
    if existing is None:
        await auth.register(
            RegisterRequest(
                email=DEMO_EMAIL,
                password=DEMO_PASSWORD,
                display_name=DEMO_NAME,
                device_id=DEMO_DEVICE,
                device_name="Seed",
            )
        )
        created_user = True
        user = await repo.get_user_by_email_hash(hash_email(DEMO_EMAIL))
    else:
        user = existing

    assert user is not None
    user_id = user.id

    receipts = ReceiptService(session)
    receipt_specs = [
        ("seed-fn-1", "seed-fd-1", "seed-fp-1", Decimal("250.00"), 2),
        ("seed-fn-2", "seed-fd-2", "seed-fp-2", Decimal("890.50"), 5),
        ("seed-fn-3", "seed-fd-3", "seed-fp-3", Decimal("120.00"), 10),
    ]
    receipts_created = 0
    for fn, fd, fp, total, days_ago in receipt_specs:
        # Stub FNS never invents merchants/items — confirm demo lines explicitly.
        out = await receipts.scan(
            user_id,
            ReceiptScanRequest(
                fn=fn,
                fd=fd,
                fp=fp,
                total_amount=total,
                purchased_at=datetime.now(UTC) - timedelta(days=days_ago),
                idempotency_key=f"seed-{fn}",
            ),
        )
        if out.status == "needs_confirmation":
            milk = (total * Decimal("0.4")).quantize(Decimal("0.01"))
            bread = (total - milk).quantize(Decimal("0.01"))
            out = await receipts.confirm(
                user_id,
                out.id,
                ReceiptConfirmRequest(
                    store_name="Пятёрочка",
                    total_amount=total,
                    purchased_at=(datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
                    items=[
                        RecognizedItem(
                            name="Молоко Простоквашино 2.5%",
                            qty=Decimal("1"),
                            price=milk,
                            sum=milk,
                            confidence=1.0,
                        ),
                        RecognizedItem(
                            name="Хлеб Бородинский",
                            qty=Decimal("1"),
                            price=bread,
                            sum=bread,
                            confidence=1.0,
                        ),
                    ],
                ),
            )
        if out.status == "done":
            receipts_created += 1

    await receipts.analyze_text(
        user_id,
        AnalyzeTextRequest(
            raw_text=(
                "Пятёрочка\n"
                "Молоко 1 100.00\n"
                "Хлеб 1 150.00\n"
                "Итого: 250.00 руб\n"
            ),
            fn="seed-ocr-fn",
            fd="seed-ocr-fd",
            fp="seed-ocr-fp",
            persist=True,
        ),
    )

    goals = GoalService(session)
    if not await goals.list_for_users([user_id]):
        await goals.create(
            user_id,
            GoalCreate(
                name="Подушка безопасности",
                target_amount=Decimal("50000"),
                currency="RUB",
            ),
        )
        await goals.create(
            user_id,
            GoalCreate(name="Отпуск", target_amount=Decimal("80000"), currency="RUB"),
        )

    budgets = BudgetService(session)
    if not await budgets.list_for_users([user_id]):
        now = datetime.now(UTC)
        start = datetime(now.year, now.month, 1, tzinfo=UTC).date()
        if now.month == 12:
            end = (datetime(now.year + 1, 1, 1, tzinfo=UTC) - timedelta(days=1)).date()
        else:
            end = (datetime(now.year, now.month + 1, 1, tzinfo=UTC) - timedelta(days=1)).date()
        await budgets.create(
            user_id,
            BudgetCreate(
                name="Месячный лимит",
                limit_amount=Decimal("30000"),
                currency="RUB",
                period_start=start,
                period_end=end,
            ),
        )

    insights = await AiService(session).insights(user_id, period="month")
    await session.commit()

    result: dict[str, object] = {
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "user_id": str(user_id),
        "created_user": created_user,
        "receipts_processed": receipts_created,
        "insights": len(insights),
    }
    logger.info(
        "berrio.demo_seed_complete",
        email=DEMO_EMAIL,
        user_id=str(user_id),
        created_user=created_user,
        receipts_processed=receipts_created,
        insights=len(insights),
    )
    return result


async def maybe_seed_on_startup() -> None:
    settings = get_settings()
    if not settings.seed_demo_data:
        return
    if settings.app_env == "production" or not settings.debug:
        logger.warning("berrio.demo_seed_skipped", reason="not development")
        return

    from app.db.session import _session_factory

    async with _session_factory()() as session:
        try:
            await seed_demo_data(session)
        except Exception as exc:  # noqa: BLE001
            logger.warning("berrio.demo_seed_failed", error=str(exc))
