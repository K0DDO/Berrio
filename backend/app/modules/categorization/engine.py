"""
Categorization engine.

Pipeline: system rules → user rules → merchant default → AI → user correction → new rule.
Business logic lands in Stage 4.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CategorizationRequest:
    name_raw: str
    merchant_id: UUID | None = None
    user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CategorizationResult:
    category_id: UUID | None
    source: str  # rules|user_rule|merchant|ai|unknown
    confidence: float = 0.0


class CategorizationEngine:
    """Facade — implementations plugged in Stage 4."""

    async def categorize(self, request: CategorizationRequest) -> CategorizationResult:
        _ = request
        return CategorizationResult(category_id=None, source="unknown", confidence=0.0)
