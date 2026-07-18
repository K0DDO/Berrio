"""Categorization domain — rules + AI fallback."""

from app.modules.categorization.engine import (
    CategorizationEngine,
    CategorizationRequest,
    CategorizationResult,
)

__all__ = [
    "CategorizationEngine",
    "CategorizationRequest",
    "CategorizationResult",
]
