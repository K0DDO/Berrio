"""Create reconciliation_matches.

Revision ID: 0011_reconciliation
Revises: 0010_notifications
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_reconciliation"
down_revision: str | None = "0010_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_matches",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey("receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="SUGGESTED"),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("receipt_id", "transaction_id", name="uq_reconciliation_receipt_tx"),
    )
    op.create_index("ix_reconciliation_matches_user_id", "reconciliation_matches", ["user_id"])
    op.create_index("ix_reconciliation_matches_receipt_id", "reconciliation_matches", ["receipt_id"])
    op.create_index(
        "ix_reconciliation_matches_transaction_id", "reconciliation_matches", ["transaction_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_reconciliation_matches_transaction_id", table_name="reconciliation_matches")
    op.drop_index("ix_reconciliation_matches_receipt_id", table_name="reconciliation_matches")
    op.drop_index("ix_reconciliation_matches_user_id", table_name="reconciliation_matches")
    op.drop_table("reconciliation_matches")
