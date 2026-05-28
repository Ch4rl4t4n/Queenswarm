"""Add Grok template library persistence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0052_grok_templates_and_context"
down_revision = "0051_billing_schema_neutralization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grok_run_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("scope_paths", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("run_mode", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("command_profile", sa.String(length=64), nullable=False),
        sa.Column("context_sources", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tags", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_grok_run_templates_tenant_updated", "grok_run_templates", ["tenant_id", "updated_at"])
    op.create_index("ix_grok_run_templates_tenant_archived", "grok_run_templates", ["tenant_id", "is_archived"])


def downgrade() -> None:
    op.drop_index("ix_grok_run_templates_tenant_archived", table_name="grok_run_templates")
    op.drop_index("ix_grok_run_templates_tenant_updated", table_name="grok_run_templates")
    op.drop_table("grok_run_templates")
