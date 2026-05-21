"""Add tenants.operator_settings JSONB for per-tenant operator tooling config."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0044_tenant_operator_settings"
down_revision = "0043_platform_feature_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "operator_settings" not in columns:
        op.add_column(
            "tenants",
            sa.Column(
                "operator_settings",
                JSONB,
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "operator_settings" in columns:
        op.drop_column("tenants", "operator_settings")
