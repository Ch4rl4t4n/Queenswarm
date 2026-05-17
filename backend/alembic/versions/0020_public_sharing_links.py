"""Phase 10.4 — public sharing links."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020_public_sharing_links"
down_revision = "0019_billing_usage_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("share_token", sa.String(length=96), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["dashboard_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token", name="uq_public_share_links_share_token"),
    )
    op.create_index("ix_public_share_links_tenant_id", "public_share_links", ["tenant_id"], unique=False)
    op.create_index("ix_public_share_links_resource_type", "public_share_links", ["resource_type"], unique=False)
    op.create_index("ix_public_share_links_resource_id", "public_share_links", ["resource_id"], unique=False)
    op.create_index("ix_public_share_links_share_token", "public_share_links", ["share_token"], unique=False)
    op.create_index("ix_public_share_links_created_by_user_id", "public_share_links", ["created_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_public_share_links_created_by_user_id", table_name="public_share_links")
    op.drop_index("ix_public_share_links_share_token", table_name="public_share_links")
    op.drop_index("ix_public_share_links_resource_id", table_name="public_share_links")
    op.drop_index("ix_public_share_links_resource_type", table_name="public_share_links")
    op.drop_index("ix_public_share_links_tenant_id", table_name="public_share_links")
    op.drop_table("public_share_links")
