"""Connector vault table for encrypted MCP / third-party credentials."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_connector_vault_entries"
down_revision = "0011_alembic_version_widen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_vault_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("credential_kind", sa.String(length=32), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("dashboard_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(
            ["dashboard_user_id"],
            ["dashboard_users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_connector_vault_entries_slug", "connector_vault_entries", ["slug"])
    op.create_index(
        "ix_connector_vault_entries_credential_kind",
        "connector_vault_entries",
        ["credential_kind"],
    )
    op.create_index(
        "ix_connector_vault_entries_dashboard_user_id",
        "connector_vault_entries",
        ["dashboard_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_connector_vault_entries_dashboard_user_id", table_name="connector_vault_entries")
    op.drop_index("ix_connector_vault_entries_credential_kind", table_name="connector_vault_entries")
    op.drop_index("ix_connector_vault_entries_slug", table_name="connector_vault_entries")
    op.drop_table("connector_vault_entries")
