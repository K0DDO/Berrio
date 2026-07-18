"""Add recognition_json for confidence metadata.

Revision ID: 0015_receipt_recognition
Revises: 0014_beta_hardening
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_receipt_recognition"
down_revision: str | None = "0014_beta_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("receipts", sa.Column("recognition_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("receipts", "recognition_json")
