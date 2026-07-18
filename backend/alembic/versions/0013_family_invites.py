"""Create family_invites.

Revision ID: 0013_family_invites
Revises: 0012_dashboard_prefs
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_family_invites"
down_revision: str | None = "0012_dashboard_prefs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "family_invites",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "family_id",
            sa.Uuid(),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invited_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email_hash", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "accepted_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("token_hash", name="uq_family_invites_token_hash"),
    )
    op.create_index("ix_family_invites_family_id", "family_invites", ["family_id"])
    op.create_index("ix_family_invites_email_hash", "family_invites", ["email_hash"])


def downgrade() -> None:
    op.drop_index("ix_family_invites_email_hash", table_name="family_invites")
    op.drop_index("ix_family_invites_family_id", table_name="family_invites")
    op.drop_table("family_invites")
