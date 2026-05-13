"""Alembic revision: operator-scoped external API credentials."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_operator_external_apis"
down_revision = "0009_dashboard_api_key_source_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operator_external_apis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["user_id"], ["dashboard_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", "label", name="uq_operator_external_user_provider_label"),
    )
    op.create_index(
        "ix_operator_external_apis_user_id",
        "operator_external_apis",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operator_external_apis_user_id", table_name="operator_external_apis")
    op.drop_table("operator_external_apis")
