from uuid import UUID

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: UUID
    parent_id: UUID | None
    slug: str
    name: str
    system_default: bool

    model_config = {"from_attributes": True}


class OverrideCategoryRequest(BaseModel):
    category_id: UUID
    create_rule: bool = Field(default=True)


class CategorizePreviewRequest(BaseModel):
    name_raw: str = Field(min_length=1, max_length=512)


class CategorizePreviewOut(BaseModel):
    category_id: UUID | None
    source: str
    confidence: float
