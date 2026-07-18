from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user_id
from app.modules.categories.schemas import (
    CategorizePreviewOut,
    CategorizePreviewRequest,
    CategoryOut,
    OverrideCategoryRequest,
)
from app.modules.categorization.service import CategorizationService
from app.modules.receipts.models import ReceiptItem
from app.modules.receipts.repository import ReceiptRepository

router = APIRouter(tags=["categories"])


def get_categorization_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategorizationService:
    return CategorizationService(session)


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    _: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[CategorizationService, Depends(get_categorization_service)],
) -> list[CategoryOut]:
    cats = await service.list_categories()
    await service._session.commit()
    return [CategoryOut.model_validate(c) for c in cats]


@router.post("/categories/preview", response_model=CategorizePreviewOut)
async def preview_categorization(
    body: CategorizePreviewRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: Annotated[CategorizationService, Depends(get_categorization_service)],
) -> CategorizePreviewOut:
    result = await service.categorize_item_name(body.name_raw, user_id=user_id)
    await service._session.commit()
    return CategorizePreviewOut(
        category_id=result.category_id,
        source=result.source,
        confidence=result.confidence,
    )


@router.post("/receipt-items/{item_id}/category", response_model=CategoryOut)
async def override_receipt_item_category(
    item_id: UUID,
    body: OverrideCategoryRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    service: Annotated[CategorizationService, Depends(get_categorization_service)],
) -> CategoryOut:
    item = await session.get(ReceiptItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item not found")
    receipt = await ReceiptRepository(session).get_by_id(item.receipt_id, user_id)
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    await service.override_item_category(
        user_id=user_id,
        item=item,
        category_id=body.category_id,
        create_rule=body.create_rule,
    )
    await session.commit()
    cats = {c.id: c for c in await service.list_categories()}
    cat = cats.get(body.category_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    return CategoryOut.model_validate(cat)
