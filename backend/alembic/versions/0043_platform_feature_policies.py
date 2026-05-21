"""Platform feature policy matrix for admin-controlled account profiles."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0043_platform_feature_policies"
down_revision = "0042_tenant_platform_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "platform_feature_policies" not in inspector.get_table_names():
        op.create_table(
            "platform_feature_policies",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("feature_key", sa.String(length=64), nullable=False),
            sa.Column("profile_key", sa.String(length=32), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("feature_key", "profile_key", name="uq_platform_feature_policy"),
        )
        op.create_index(
            "ix_platform_feature_policies_feature_key",
            "platform_feature_policies",
            ["feature_key"],
            unique=False,
        )
        op.create_index(
            "ix_platform_feature_policies_profile_key",
            "platform_feature_policies",
            ["profile_key"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "platform_feature_policies" in inspector.get_table_names():
        op.drop_index("ix_platform_feature_policies_profile_key", table_name="platform_feature_policies")
        op.drop_index("ix_platform_feature_policies_feature_key", table_name="platform_feature_policies")
        op.drop_table("platform_feature_policies")
