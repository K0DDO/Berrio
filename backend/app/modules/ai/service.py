from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.ai_client import AiClient, get_ai_client
from app.modules.ai.models import AiFeedbackType, AiInsight, AiInsightFeedback
from app.modules.analytics.service import AnalyticsService

# Process-local chat cache + simple rate limit (per user)
_CHAT_CACHE: OrderedDict[str, tuple[float, str]] = OrderedDict()
_CHAT_CACHE_TTL_SEC = 300
_CHAT_CACHE_MAX = 256
_RATE: dict[str, list[float]] = {}
_RATE_MAX_PER_HOUR = 60


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    period: str = "month"


class AiChatResponse(BaseModel):
    reply: str
    provider: str
    context_period: str
    total_spend: str | None = None
    berrio_score: int | None = None
    cached: bool = False


class AiInsightOut(BaseModel):
    id: UUID | None = None
    title: str
    body: str
    kind: str


class AiFeedbackRequest(BaseModel):
    feedback_type: AiFeedbackType
    rating: int = Field(default=0, ge=-1, le=1)


class AiFeedbackOut(BaseModel):
    id: UUID
    insight_id: UUID
    feedback_type: str
    rating: int


SYSTEM_PROMPT = (
    "Ты Berrio — спокойный AI-экономист. Объясняй просто, без стыда за траты. "
    "Используй ТОЛЬКО факты из блока «Контекст». Не выдумывай суммы, магазины и проценты. "
    "Если дохода мало и еда занимает большую долю — не советуй «экономить на еде»; "
    "скажи, что узкое место скорее в уровне дохода. "
    "Если данных мало — честно скажи, чего не хватает. Отвечай на русском."
)


class AiService:
    def __init__(self, session: AsyncSession, client: AiClient | None = None) -> None:
        self._session = session
        self._client = client or get_ai_client()
        self._analytics = AnalyticsService(session)

    async def chat(self, user_id: UUID, body: AiChatRequest) -> AiChatResponse:
        self._enforce_rate_limit(user_id)
        summary = await self._analytics.summary(user_id, period=body.period)
        context = self._build_context(summary)
        cache_key = hashlib.sha256(
            f"{user_id}:{body.period}:{body.message}:{summary.total_spend}".encode()
        ).hexdigest()
        cached = self._cache_get(cache_key)
        if cached is not None:
            return AiChatResponse(
                reply=cached,
                provider="cache",
                context_period=body.period,
                total_spend=str(summary.total_spend),
                berrio_score=summary.berrio_score,
                cached=True,
            )

        reply = await self._client.complete(
            system=SYSTEM_PROMPT,
            user=f"Контекст:\n{context}\n\nВопрос пользователя:\n{body.message}",
        )
        self._cache_set(cache_key, reply)
        provider = "kimi" if get_settings().kimi_api_key else "stub"
        return AiChatResponse(
            reply=reply,
            provider=provider,
            context_period=body.period,
            total_spend=str(summary.total_spend),
            berrio_score=summary.berrio_score,
            cached=False,
        )

    async def insights(self, user_id: UUID, *, period: str = "month") -> list[AiInsightOut]:
        from datetime import UTC, datetime, timedelta

        recent = await self._session.execute(
            select(AiInsight)
            .where(AiInsight.user_id == user_id, AiInsight.period == period)
            .order_by(AiInsight.created_at.desc())
            .limit(10)
        )
        rows = list(recent.scalars().all())
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        fresh = []
        for r in rows:
            created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=UTC)
            if created >= cutoff:
                fresh.append(r)
        if fresh:
            return [AiInsightOut(id=r.id, title=r.title, body=r.body, kind=r.kind) for r in fresh]

        summary = await self._analytics.summary(user_id, period=period)
        drafts: list[AiInsightOut] = []
        factors = summary.score_factors or {}
        income = factors.get("income")
        if summary.total_spend > 0 and summary.by_category:
            lines = []
            for cat in summary.by_category[:5]:
                lines.append(f"{cat.category_name} {cat.share:.0%}")
            cats_block = "\n".join(lines)
            top = summary.by_category[0]
            if income and Decimal(str(income)) < Decimal("60000") and top.share >= 0.35:
                advice = (
                    f"«{top.category_name}» — крупная статья ({top.share:.0%}). "
                    "При текущем доходе это скорее сигнал про уровень заработка, "
                    "а не про «лишние» траты."
                )
            else:
                tip_amount = (top.amount * Decimal("0.1")).quantize(Decimal("1"))
                advice = (
                    f"Можно точечно пересмотреть «{top.category_name.lower()}» "
                    f"(ориентир экономии ~{tip_amount} ₽), если это необязательные покупки."
                )
            drafts.append(
                AiInsightOut(
                    title="Разбор трат за период",
                    body=(
                        f"Расходы: {summary.total_spend} ₽\n\n"
                        f"Основные категории:\n{cats_block}\n\n"
                        f"Рекомендация:\n{advice}"
                    ),
                    kind="first_insight",
                )
            )
        merchants = getattr(summary, "top_merchants", None) or []
        if merchants:
            m = merchants[0]
            drafts.append(
                AiInsightOut(
                    title="Куда уходят деньги",
                    body=(
                        f"{m.store_name}: {m.purchase_count} покупок на {m.amount} ₽ "
                        f"за период «{summary.period}»."
                    ),
                    kind="merchants",
                )
            )
        if summary.berrio_score is not None:
            drafts.append(
                AiInsightOut(
                    title="Berrio Score",
                    body=f"Оценка финансового здоровья: {summary.berrio_score}/100.",
                    kind="health",
                )
            )
        if not drafts:
            drafts.append(
                AiInsightOut(
                    title="Начните со скана чека",
                    body="Пока мало данных. Отсканируйте QR чека — аналитика появится автоматически.",
                    kind="onboarding",
                )
            )

        out: list[AiInsightOut] = []
        for item in drafts:
            row = AiInsight(
                user_id=user_id,
                period=period,
                kind=item.kind,
                title=item.title,
                body=item.body,
                payload_json=json.dumps(
                    {"total_spend": str(summary.total_spend), "score": summary.berrio_score},
                    ensure_ascii=False,
                ),
            )
            self._session.add(row)
            await self._session.flush()
            out.append(AiInsightOut(id=row.id, title=row.title, body=row.body, kind=row.kind))
        return out

    async def monthly_review(self, user_id: UUID) -> AiInsightOut:
        """Secondary monthly narrative built only from analytics facts."""
        from app.core.config import get_settings

        summary = await self._analytics.summary(user_id, period="month")
        factors = summary.score_factors or {}
        lines = [f"За месяц потрачено {summary.total_spend} ₽ ({summary.receipt_count} чеков)."]
        if summary.avg_receipt is not None:
            lines.append(f"Средний чек: {summary.avg_receipt} ₽.")
        if summary.by_category:
            lines.append("Основные статьи:")
            for cat in summary.by_category[:5]:
                lines.append(f"• {cat.category_name}: {cat.amount} ₽ ({cat.share:.0%})")
        merchants = getattr(summary, "top_merchants", None) or []
        if merchants:
            lines.append("Куда уходят деньги:")
            for m in merchants[:5]:
                lines.append(f"• {m.store_name}: {m.purchase_count} пок. / {m.amount} ₽")
        for p in factors.get("positive") or []:
            lines.append(f"+ {p}")
        for n in factors.get("negative") or []:
            lines.append(f"− {n}")
        if summary.berrio_score is not None:
            lines.append(f"Berrio Score: {summary.berrio_score}/100.")
        provider = "kimi" if get_settings().kimi_api_key else "stub"
        body = "\n".join(lines)
        if provider == "stub":
            body = "[Локальный режим]\n" + body
        row = AiInsight(
            user_id=user_id,
            period="month",
            kind="monthly_review",
            title="Разбор месяца",
            body=body,
            payload_json=json.dumps(
                {"provider": provider, "total_spend": str(summary.total_spend)},
                ensure_ascii=False,
            ),
        )
        self._session.add(row)
        await self._session.flush()
        return AiInsightOut(id=row.id, title=row.title, body=row.body, kind=row.kind)

    async def submit_feedback(
        self,
        user_id: UUID,
        insight_id: UUID,
        body: AiFeedbackRequest,
    ) -> AiFeedbackOut:
        insight = await self._session.get(AiInsight, insight_id)
        if insight is None or insight.user_id != user_id:
            from fastapi import HTTPException, status

            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Insight not found")

        rating = body.rating
        if rating == 0:
            rating = 1 if body.feedback_type == AiFeedbackType.HELPFUL else -1

        result = await self._session.execute(
            select(AiInsightFeedback).where(
                AiInsightFeedback.insight_id == insight_id,
                AiInsightFeedback.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = AiInsightFeedback(
                insight_id=insight_id,
                user_id=user_id,
                feedback_type=body.feedback_type.value,
                rating=rating,
            )
            self._session.add(row)
        else:
            row.feedback_type = body.feedback_type.value
            row.rating = rating
        await self._session.flush()
        return AiFeedbackOut(
            id=row.id,
            insight_id=row.insight_id,
            feedback_type=row.feedback_type,
            rating=row.rating,
        )

    @staticmethod
    def _build_context(summary) -> str:
        top = (
            ", ".join(
                f"{c.category_name}: {c.amount} ({c.share:.0%})" for c in summary.by_category[:5]
            )
            or "нет данных"
        )
        merchants = ""
        if getattr(summary, "top_merchants", None):
            merchants = "; ".join(
                f"{m.store_name}: {m.purchase_count} пок. / {m.amount} ₽"
                for m in summary.top_merchants[:5]
            )
        factors = summary.score_factors or {}
        income = factors.get("income")
        return (
            f"Период: {summary.period}. Расходы: {summary.total_spend} ₽. "
            f"Чеков: {summary.receipt_count}. Средний чек: {getattr(summary, 'avg_receipt', None)}. "
            f"Доход (если указан): {income}. Berrio Score: {summary.berrio_score}. "
            f"Топ категорий: {top}. "
            f"Куда уходят деньги (магазины): {merchants or 'нет'}. "
            f"Плюсы: {factors.get('positive')}. Минусы: {factors.get('negative')}."
        )

    @staticmethod
    def _enforce_rate_limit(user_id: UUID) -> None:
        from fastapi import HTTPException, status

        key = str(user_id)
        now = time.time()
        window = _RATE.setdefault(key, [])
        _RATE[key] = [t for t in window if now - t < 3600]
        if len(_RATE[key]) >= _RATE_MAX_PER_HOUR:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI rate limit exceeded (60 requests/hour)",
            )
        _RATE[key].append(now)

    @staticmethod
    def _cache_get(key: str) -> str | None:
        item = _CHAT_CACHE.get(key)
        if item is None:
            return None
        ts, value = item
        if time.time() - ts > _CHAT_CACHE_TTL_SEC:
            _CHAT_CACHE.pop(key, None)
            return None
        return value

    @staticmethod
    def _cache_set(key: str, value: str) -> None:
        _CHAT_CACHE[key] = (time.time(), value)
        while len(_CHAT_CACHE) > _CHAT_CACHE_MAX:
            _CHAT_CACHE.popitem(last=False)
