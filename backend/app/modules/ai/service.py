from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.ai_client import AiClient, get_ai_client
from app.modules.analytics.service import AnalyticsService


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    period: str = "month"


class AiChatResponse(BaseModel):
    reply: str
    provider: str
    context_period: str
    total_spend: str | None = None
    berrio_score: int | None = None


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
        summary = await self._analytics.summary(user_id, period=body.period)
        top = ", ".join(
            f"{c.category_name}: {c.amount}" for c in summary.by_category[:5]
        ) or "нет данных"
        context = (
            f"Период: {summary.period}. Сумма расходов: {summary.total_spend}. "
            f"Чеков: {summary.receipt_count}. Berrio Score: {summary.berrio_score}. "
            f"Топ категорий: {top}. Факторы: {summary.score_factors}."
        )
        reply = await self._client.complete(
            system=SYSTEM_PROMPT,
            user=f"Контекст:\n{context}\n\nВопрос пользователя:\n{body.message}",
        )
        from app.core.config import get_settings

        provider = "kimi" if get_settings().kimi_api_key else "stub"
        return AiChatResponse(
            reply=reply,
            provider=provider,
            context_period=body.period,
            total_spend=str(summary.total_spend),
            berrio_score=summary.berrio_score,
        )

    async def insights(self, user_id: UUID, *, period: str = "month") -> list[AiInsightOut]:
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
        return insights
