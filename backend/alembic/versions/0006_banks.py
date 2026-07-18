"""Create bank_connections and transactions.

Revision ID: 0006_banks
Revises: 0005_financial_scores
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_banks"
down_revision: str | None = "0005_financial_scores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bank_connections",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_bank_connections_user_id", "bank_connections", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="BANK"),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("merchant_raw", sa.String(length=255), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=True),
        sa.Column("booked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("bank_connection_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="posted"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "external_id", name="uq_transactions_user_external"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_bank_connections_user_id", table_name="bank_connections")
    op.drop_table("bank_connections")
