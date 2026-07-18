from __future__ import annotations

from typing import Protocol

from app.core.config import get_settings


class AiClient(Protocol):
    async def complete(self, *, system: str, user: str) -> str: ...


class StubAiClient:
    """Deterministic local economist — used when KIMI_API_KEY is unset."""

    async def complete(self, *, system: str, user: str) -> str:
        _ = system
        lower = user.lower()
        if "ноутбук" in lower or "laptop" in lower:
            return (
                "При текущих тратах лучше сначала зафиксировать цель накопления. "
                "Если откладывать 10–15% свободного бюджета, покупка станет реалистичнее за несколько месяцев. "
                "Могу помочь разложить расходы и найти необязательные категории."
            )
        if "кофе" in lower or "доставк" in lower:
            return (
                "Необязательные расходы (кофе/доставка) часто растут незаметно. "
                "Сокращение на 20% обычно даёт ощутимую экономию без жёстких ограничений. "
                "Сверьтесь с аналитикой за месяц по категориям."
            )
        return (
            "Я Berrio AI — ваш финансовый экономист. "
            "Покажите период или задайте вопрос о тратах, целях или покупке. "
            "Рекомендации опираются на ваши чеки и категории."
        )


class KimiAiClient:
    """Kimi/Moonshot HTTP client — enabled when KIMI_API_KEY is set."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(self, *, system: str, user: str) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.4,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


def get_ai_client() -> AiClient:
    settings = get_settings()
    if settings.kimi_api_key:
        return KimiAiClient(
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            model=settings.kimi_model,
        )
    return StubAiClient()
