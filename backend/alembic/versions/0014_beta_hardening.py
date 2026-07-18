"""AI feedback + beta performance indexes.

Revision ID: 0014_beta_hardening
Revises: 0013_family_invites
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_beta_hardening"
down_revision: str | None = "0013_family_invites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_insight_feedback",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "insight_id",
            sa.Uuid(),
            sa.ForeignKey("ai_insights.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("insight_id", "user_id", name="uq_ai_insight_feedback_insight_user"),
    )
    op.create_index("ix_ai_insight_feedback_insight_id", "ai_insight_feedback", ["insight_id"])
    op.create_index("ix_ai_insight_feedback_user_id", "ai_insight_feedback", ["user_id"])
    op.create_index(
        "ix_ai_insight_feedback_type",
        "ai_insight_feedback",
        ["feedback_type"],
    )

    # Hot-path indexes for beta analytics / lists
    op.create_index("ix_receipts_user_purchased_at", "receipts", ["user_id", "purchased_at"])
    op.create_index("ix_receipts_user_status", "receipts", ["user_id", "status"])
    op.create_index("ix_receipts_family_id", "receipts", ["family_id"])
    op.create_index("ix_receipt_items_category_id", "receipt_items", ["category_id"])
    op.create_index("ix_receipt_items_product_variant_id", "receipt_items", ["product_variant_id"])
    op.create_index("ix_transactions_user_booked_at", "transactions", ["user_id", "booked_at"])
    op.create_index("ix_transactions_family_id", "transactions", ["family_id"])
    op.create_index(
        "ix_product_price_history_variant_purchased",
        "product_price_history",
        ["product_variant_id", "purchased_at"],
    )
    op.create_index("ix_ai_insights_user_created", "ai_insights", ["user_id", "created_at"])
    op.create_index(
        "ix_reconciliation_matches_user_status",
        "reconciliation_matches",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_reconciliation_matches_user_status", table_name="reconciliation_matches")
    op.drop_index("ix_ai_insights_user_created", table_name="ai_insights")
    op.drop_index("ix_product_price_history_variant_purchased", table_name="product_price_history")
    op.drop_index("ix_transactions_family_id", table_name="transactions")
    op.drop_index("ix_transactions_user_booked_at", table_name="transactions")
    op.drop_index("ix_receipt_items_product_variant_id", table_name="receipt_items")
    op.drop_index("ix_receipt_items_category_id", table_name="receipt_items")
    op.drop_index("ix_receipts_family_id", table_name="receipts")
    op.drop_index("ix_receipts_user_status", table_name="receipts")
    op.drop_index("ix_receipts_user_purchased_at", table_name="receipts")
    op.drop_index("ix_ai_insight_feedback_type", table_name="ai_insight_feedback")
    op.drop_index("ix_ai_insight_feedback_user_id", table_name="ai_insight_feedback")
    op.drop_index("ix_ai_insight_feedback_insight_id", table_name="ai_insight_feedback")
    op.drop_table("ai_insight_feedback")
