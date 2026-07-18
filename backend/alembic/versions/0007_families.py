"""Create families, family_members, family_permissions.

Revision ID: 0007_families
Revises: 0006_banks
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_families"
down_revision: str | None = "0006_banks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "families",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "family_members",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("family_id", sa.Uuid(), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("family_id", "user_id", name="uq_family_members_family_user"),
    )
    op.create_index("ix_family_members_family_id", "family_members", ["family_id"])
    op.create_index("ix_family_members_user_id", "family_members", ["user_id"])

    op.create_table(
        "family_permissions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("family_id", sa.Uuid(), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "member_id",
            sa.Uuid(),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("permission_key", sa.String(length=64), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint(
            "family_id", "member_id", "permission_key", name="uq_family_permissions_member_key"
        ),
    )
    op.create_index("ix_family_permissions_member_id", "family_permissions", ["member_id"])


def downgrade() -> None:
    op.drop_index("ix_family_permissions_member_id", table_name="family_permissions")
    op.drop_table("family_permissions")
    op.drop_index("ix_family_members_user_id", table_name="family_members")
    op.drop_index("ix_family_members_family_id", table_name="family_members")
    op.drop_table("family_members")
    op.drop_table("families")
