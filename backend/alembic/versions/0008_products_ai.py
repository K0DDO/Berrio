"""Create products, product_variants, product_price_history, ai_insights.

Revision ID: 0008_products_ai
Revises: 0007_families
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_products_ai"
down_revision: str | None = "0007_families"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("weight", sa.Numeric(14, 3), nullable=True),
        sa.Column("volume", sa.Numeric(14, 3), nullable=True),
        sa.Column("unit", sa.String(length=16), nullable=False, server_default="pcs"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("barcode", name="uq_product_variants_barcode"),
        sa.UniqueConstraint(
            "product_id", "weight", "volume", "unit", name="uq_product_variants_dims"
        ),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    op.create_table(
        "product_price_history",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "product_variant_id",
            sa.Uuid(),
            sa.ForeignKey("product_variants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("store_name", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_item_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_product_price_history_product_variant_id",
        "product_price_history",
        ["product_variant_id"],
    )
    op.create_index("ix_product_price_history_user_id", "product_price_history", ["user_id"])

    op.create_table(
        "ai_insights",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_insights_user_id", "ai_insights", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_insights_user_id", table_name="ai_insights")
    op.drop_table("ai_insights")
    op.drop_index("ix_product_price_history_user_id", table_name="product_price_history")
    op.drop_index(
        "ix_product_price_history_product_variant_id", table_name="product_price_history"
    )
    op.drop_table("product_price_history")
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_table("products")
