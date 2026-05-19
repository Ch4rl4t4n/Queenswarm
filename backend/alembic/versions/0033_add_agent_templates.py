"""Add tenant-scoped dynamic agent templates."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0033_add_agent_templates"
down_revision = "0030_add_goals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create `agent_templates` table for dynamic /agents/new catalog."""

    op.create_table(
        "agent_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("icon", sa.String(length=32), nullable=False, server_default=sa.text("''")),
        sa.Column("category", sa.String(length=64), nullable=False, server_default=sa.text("'general'")),
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("prompt_template", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_templates_tenant_id", "agent_templates", ["tenant_id"], unique=False)
    op.create_index("ix_agent_templates_category", "agent_templates", ["category"], unique=False)


def downgrade() -> None:
    """Drop dynamic agent templates table."""

    op.drop_index("ix_agent_templates_category", table_name="agent_templates")
    op.drop_index("ix_agent_templates_tenant_id", table_name="agent_templates")
    op.drop_table("agent_templates")
