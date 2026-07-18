"""Add notification_preferences, dedupe_key, reconciliation confidence.

Revision ID: 0012_dashboard_prefs
Revises: 0011_reconciliation
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_dashboard_prefs"
down_revision: str | None = "0011_reconciliation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_changes_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("budget_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("goal_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ai_insights_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "unusual_spending_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])

    op.add_column("notifications", sa.Column("dedupe_key", sa.String(length=191), nullable=True))
    op.create_unique_constraint(
        "uq_notifications_user_dedupe", "notifications", ["user_id", "dedupe_key"]
    )

    op.add_column(
        "reconciliation_matches",
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("reconciliation_matches", "confidence")
    op.drop_constraint("uq_notifications_user_dedupe", "notifications", type_="unique")
    op.drop_column("notifications", "dedupe_key")
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
