"""Machine-stable ``source_name`` for dashboard API keys (integration identity)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_dashboard_api_key_source_name"
down_revision = "0008_hive_llm_secrets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_api_keys",
        sa.Column("source_name", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "ix_uq_dashboard_api_keys_user_source_active",
        "dashboard_api_keys",
        ["user_id", "source_name"],
        unique=True,
        postgresql_where=sa.text("source_name IS NOT NULL AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_uq_dashboard_api_keys_user_source_active", table_name="dashboard_api_keys")
    op.drop_column("dashboard_api_keys", "source_name")
