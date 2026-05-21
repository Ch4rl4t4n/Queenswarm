"""Add tenant.platform_mode for internal operator vs commercial customer split."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0042_tenant_platform_mode"
down_revision = "0041_product_mission_factory_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "platform_mode" not in columns:
        op.add_column(
            "tenants",
            sa.Column(
                "platform_mode",
                sa.String(length=24),
                nullable=False,
                server_default="internal",
            ),
        )
        op.create_index("ix_tenants_platform_mode", "tenants", ["platform_mode"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("tenants")}
    if "platform_mode" in columns:
        op.drop_index("ix_tenants_platform_mode", table_name="tenants")
        op.drop_column("tenants", "platform_mode")
