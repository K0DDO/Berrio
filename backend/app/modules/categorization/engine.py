from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.categories.models import Category, CategoryRule


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
    """Facade — rules → AI."""

    async def categorize(self, request: CategorizationRequest) -> CategorizationResult:
        _ = request
        return CategorizationResult(category_id=None, source="unknown", confidence=0.0)


@dataclass(frozen=True, slots=True)
class _RuleView:
    pattern: str
    match_type: str
    category_id: UUID
    priority: int
    source: str


class RuleBasedCategorizationEngine(CategorizationEngine):
    """Pipeline: user rules (boosted) → system rules → unknown."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def categorize(self, request: CategorizationRequest) -> CategorizationResult:
        name = request.name_raw.strip().lower()
        if not name:
            return CategorizationResult(category_id=None, source="unknown", confidence=0.0)

        rules = await self._load_rules(request.user_id)
        for rule in rules:
            if self._matches(name, rule.pattern.lower(), rule.match_type):
                return CategorizationResult(
                    category_id=rule.category_id,
                    source=rule.source,
                    confidence=0.95 if rule.source == "user_rule" else 0.8,
                )
        return CategorizationResult(category_id=None, source="unknown", confidence=0.0)

    async def _load_rules(self, user_id: UUID | None) -> list[_RuleView]:
        conditions: list = [CategoryRule.user_id.is_(None)]
        if user_id is not None:
            conditions.append(CategoryRule.user_id == user_id)
        result = await self._session.execute(
            select(CategoryRule).where(or_(*conditions)).order_by(CategoryRule.priority.asc())
        )
        rows = list(result.scalars().all())
        views = [
            _RuleView(
                pattern=r.pattern,
                match_type=r.match_type,
                category_id=r.category_id,
                priority=r.priority - (50 if r.user_id is not None else 0),
                source="user_rule" if r.user_id is not None else "rules",
            )
            for r in rows
        ]
        views.sort(key=lambda v: v.priority)
        return views

    @staticmethod
    def _matches(name: str, pattern: str, match_type: str) -> bool:
        if match_type == "exact":
            return name == pattern
        if match_type == "regex":
            try:
                return re.search(pattern, name, re.IGNORECASE) is not None
            except re.error:
                return False
        return pattern in name


class AiFallbackCategorizationEngine(CategorizationEngine):
    """Rules first; keyword stub marks source=ai when no rule matched."""

    def __init__(self, inner: CategorizationEngine) -> None:
        self._inner = inner

    async def categorize(self, request: CategorizationRequest) -> CategorizationResult:
        result = await self._inner.categorize(request)
        if result.category_id is not None:
            return result
        name = request.name_raw.lower()
        keywords = ("кофе", "coffee", "молоко", "хлеб", "доставка", "книга")
        if any(k in name for k in keywords):
            return CategorizationResult(category_id=None, source="ai", confidence=0.55)
        return result


async def seed_default_categories(session: AsyncSession) -> dict[str, UUID]:
    """Idempotent hierarchical defaults + system rules."""
    tree: list[tuple[str, str, str | None]] = [
        ("food", "Еда", None),
        ("food.grocery", "Продукты", "food"),
        ("food.dairy", "Молочка", "food.grocery"),
        ("food.meat", "Мясо", "food.grocery"),
        ("food.veg", "Овощи", "food.grocery"),
        ("food.cafe", "Кафе", "food"),
        ("food.delivery", "Доставка", "food"),
        ("home", "Дом", None),
        ("home.chem", "Бытовая химия", "home"),
        ("growth", "Развитие", None),
        ("growth.books", "Книги", "growth"),
        ("other", "Другое", None),
    ]
    existing = await session.execute(select(Category))
    by_slug = {c.slug: c for c in existing.scalars().all()}

    for slug, name, parent_slug in tree:
        if slug in by_slug:
            continue
        parent_id = by_slug[parent_slug].id if parent_slug and parent_slug in by_slug else None
        cat = Category(slug=slug, name=name, parent_id=parent_id, system_default=True)
        session.add(cat)
        await session.flush()
        by_slug[slug] = cat

    system_patterns = [
        ("молоко", "contains", "food.dairy", 10),
        ("простоквашино", "contains", "food.dairy", 10),
        ("хлеб", "contains", "food.grocery", 20),
        ("кофе", "contains", "food.cafe", 20),
        ("книга", "contains", "growth.books", 30),
    ]
    for pattern, match_type, slug, priority in system_patterns:
        cat = by_slug[slug]
        found = await session.execute(
            select(CategoryRule).where(
                CategoryRule.user_id.is_(None),
                CategoryRule.pattern == pattern,
                CategoryRule.match_type == match_type,
            )
        )
        if found.scalar_one_or_none() is None:
            session.add(
                CategoryRule(
                    user_id=None,
                    pattern=pattern,
                    match_type=match_type,
                    category_id=cat.id,
                    priority=priority,
                )
            )
    await session.flush()
    return {slug: c.id for slug, c in by_slug.items()}
