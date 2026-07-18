from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.ai_client import AiClient, get_ai_client
from app.modules.ai.models import AiInsight
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
    title: str
    body: str
    kind: str


SYSTEM_PROMPT = (
    "Ты Berrio — спокойный AI-экономист. Объясняй просто, без стыда за траты. "
    "Опирайся на факты из контекста пользователя. Отвечай на русском."
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
            return [AiInsightOut(title=r.title, body=r.body, kind=r.kind) for r in fresh]

        summary = await self._analytics.summary(user_id, period=period)
        insights: list[AiInsightOut] = []
        if summary.by_category:
            top = summary.by_category[0]
            insights.append(
                AiInsightOut(
                    title="Главная категория расходов",
                    body=f"{top.category_name} — {top.amount} ₽ ({top.share:.0%} за период).",
                    kind="spend_focus",
                )
            )
        if summary.berrio_score is not None:
            insights.append(
                AiInsightOut(
                    title="Berrio Score",
                    body=f"Оценка финансового здоровья: {summary.berrio_score}/100.",
                    kind="health",
                )
            )
        if not insights:
            insights.append(
                AiInsightOut(
                    title="Начните со скана чека",
                    body="Пока мало данных. Отсканируйте QR чека — аналитика появится автоматически.",
                    kind="onboarding",
                )
            )

        for item in insights:
            self._session.add(
                AiInsight(
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
            )
        await self._session.flush()
        return insights

    @staticmethod
    def _build_context(summary) -> str:
        top = ", ".join(
            f"{c.category_name}: {c.amount}" for c in summary.by_category[:5]
        ) or "нет данных"
        return (
            f"Период: {summary.period}. Сумма расходов: {summary.total_spend}. "
            f"Чеков: {summary.receipt_count}. Berrio Score: {summary.berrio_score}. "
            f"Топ категорий: {top}. Факторы: {summary.score_factors}."
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
