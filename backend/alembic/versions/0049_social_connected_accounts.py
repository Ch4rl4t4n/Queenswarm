"""Add social_connected_accounts for multi-account social publish."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0049_social_connected_accounts"
down_revision = "0048_solo_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_connected_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dashboard_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("dashboard_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("account_key", sa.String(length=256), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("oauth_provider_key", sa.String(length=64), nullable=False),
        sa.Column("connector_slug", sa.String(length=64), nullable=False),
        sa.Column("external_user_id", sa.String(length=128), nullable=True),
        sa.Column("external_username", sa.String(length=128), nullable=True),
        sa.Column("profile_meta", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("secrets_cipher", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "channel",
            "account_key",
            name="uq_social_connected_accounts_tenant_channel_key",
        ),
    )
    op.create_index(
        "ix_social_connected_accounts_tenant_channel",
        "social_connected_accounts",
        ["tenant_id", "channel"],
    )
    op.create_index(
        "ix_social_connected_accounts_tenant_default",
        "social_connected_accounts",
        ["tenant_id", "channel", "is_default"],
    )


def downgrade() -> None:
    op.drop_index("ix_social_connected_accounts_tenant_default", table_name="social_connected_accounts")
    op.drop_index("ix_social_connected_accounts_tenant_channel", table_name="social_connected_accounts")
    op.drop_table("social_connected_accounts")
