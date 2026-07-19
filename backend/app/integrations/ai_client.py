from __future__ import annotations

import time
from typing import Protocol

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class AiClient(Protocol):
    async def complete(self, *, system: str, user: str) -> str: ...


class StubAiClient:
    """Deterministic local economist — used when KIMI_API_KEY is unset.

    Explicitly labels itself; does not invent deep personal analysis.
    """

    async def complete(self, *, system: str, user: str) -> str:
        _ = system
        logger.info("ai.request", provider="stub", user_chars=len(user))
        lower = user.lower()
        if "доход" in lower and ("мал" in lower or "низк" in lower):
            reply = (
                "[Локальный режим] При небольшом доходе фокус не на «срезать еду», "
                "а на росте заработка и обязательных платежах. "
                "Пришлите цифры дохода и категорий — разберём точнее после подключения Kimi."
            )
        elif "ноутбук" in lower or "laptop" in lower:
            reply = (
                "[Локальный режим] Для крупной покупки зафиксируйте цель накопления "
                "и долю свободного бюджета. Без ключа Kimi это общий совет, не персональный разбор."
            )
        else:
            reply = (
                "[Локальный режим] KIMI_API_KEY не задан — ответы шаблонные. "
                "Опирайтесь на экран аналитики: категории, магазины и Berrio Score. "
                "Задайте вопрос после настройки Kimi для персонального разбора."
            )
        logger.info("ai.response", provider="stub", reply_chars=len(reply))
        return reply


class KimiAiClient:
    """Kimi/Moonshot HTTP client — enabled when KIMI_API_KEY is set."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(self, *, system: str, user: str) -> str:
        import httpx

        started = time.perf_counter()
        logger.info(
            "ai.request",
            provider="kimi",
            model=self._model,
            system_chars=len(system),
            user_chars=len(user),
        )
        try:
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
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()
                reply = data["choices"][0]["message"]["content"]
            logger.info(
                "ai.response",
                provider="kimi",
                reply_chars=len(reply),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            return reply
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "ai.error",
                provider="kimi",
                error=type(exc).__name__,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            raise


def get_ai_client() -> AiClient:
    settings = get_settings()
    if settings.kimi_api_key:
        return KimiAiClient(
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            model=settings.kimi_model,
        )
    return StubAiClient()
