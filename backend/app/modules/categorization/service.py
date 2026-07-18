from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.categories.models import Category, CategoryRule
from app.modules.categorization.engine import (
    AiFallbackCategorizationEngine,
    CategorizationRequest,
    CategorizationResult,
    RuleBasedCategorizationEngine,
    seed_default_categories,
)
from app.modules.receipts.models import ReceiptItem


class CategorizationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        rules = RuleBasedCategorizationEngine(session)
        self._engine = AiFallbackCategorizationEngine(rules)

    async def ensure_defaults(self) -> dict[str, UUID]:
        return await seed_default_categories(self._session)

    async def categorize_item_name(
        self, name_raw: str, *, user_id: UUID | None = None
    ) -> CategorizationResult:
        await self.ensure_defaults()
        result = await self._engine.categorize(
            CategorizationRequest(name_raw=name_raw, user_id=user_id)
        )
        if result.category_id is not None:
            return result
        if result.source == "ai":
            # Resolve keyword stub to category id
            slugs = await self.ensure_defaults()
            name = name_raw.lower()
            mapping = [
                ("кофе", "food.cafe"),
                ("молоко", "food.dairy"),
                ("хлеб", "food.grocery"),
                ("доставка", "food.delivery"),
                ("книга", "growth.books"),
            ]
            for key, slug in mapping:
                if key in name and slug in slugs:
                    return CategorizationResult(
                        category_id=slugs[slug], source="ai", confidence=0.55
                    )
        # Fallback other
        slugs = await self.ensure_defaults()
        return CategorizationResult(
            category_id=slugs.get("other"),
            source="unknown",
            confidence=0.1,
        )

    async def apply_to_receipt_items(self, items: list[ReceiptItem], *, user_id: UUID) -> int:
        updated = 0
        for item in items:
            if item.category_id is not None:
                continue
            result = await self.categorize_item_name(item.name_raw, user_id=user_id)
            if result.category_id is not None:
                item.category_id = result.category_id
                updated += 1
        await self._session.flush()
        return updated

    async def override_item_category(
        self,
        *,
        user_id: UUID,
        item: ReceiptItem,
        category_id: UUID,
        create_rule: bool = True,
    ) -> CategoryRule | None:
        item.category_id = category_id
        rule = None
        if create_rule:
            pattern = item.name_raw.strip()[:255]
            existing = await self._session.execute(
                select(CategoryRule).where(
                    CategoryRule.user_id == user_id,
                    CategoryRule.pattern == pattern,
                    CategoryRule.match_type == "contains",
                )
            )
            rule = existing.scalar_one_or_none()
            if rule is None:
                rule = CategoryRule(
                    user_id=user_id,
                    pattern=pattern,
                    match_type="contains",
                    category_id=category_id,
                    priority=1,
                )
                self._session.add(rule)
            else:
                rule.category_id = category_id
        await self._session.flush()
        return rule

    async def list_categories(self) -> list[Category]:
        await self.ensure_defaults()
        result = await self._session.execute(select(Category).order_by(Category.slug))
        return list(result.scalars().all())
