"""Receipt item display name + user finance prefs for health score.

Revision ID: 0016_helper_upgrade
Revises: 0015_receipt_recognition
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_helper_upgrade"
down_revision: str | None = "0015_receipt_recognition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "receipt_items",
        sa.Column("name_display", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("monthly_income", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("monthly_obligations", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("monthly_savings_target", sa.Numeric(14, 2), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("ignore_receipt_time_default", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "merchant_receipt_templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("merchant_key", sa.String(80), nullable=False, index=True),
        sa.Column("pattern", sa.String(255), nullable=False),
        sa.Column("name_template", sa.String(255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("merchant_receipt_templates")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "ignore_receipt_time_default")
    op.drop_column("users", "monthly_savings_target")
    op.drop_column("users", "monthly_obligations")
    op.drop_column("users", "monthly_income")
    op.drop_column("receipt_items", "name_display")
