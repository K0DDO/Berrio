"""Create categories and category_rules.

Revision ID: 0004_categories
Revises: 0003_receipts
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_categories"
down_revision: str | None = "0003_receipts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("system_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])

    op.create_table(
        "category_rules",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("pattern", sa.String(length=255), nullable=False),
        sa.Column("match_type", sa.String(length=32), nullable=False, server_default="contains"),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "pattern", "match_type", name="uq_category_rules_user_pattern"),
    )
    op.create_index("ix_category_rules_user_id", "category_rules", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_category_rules_user_id", table_name="category_rules")
    op.drop_table("category_rules")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_table("categories")
