"""Add tenant-scoped dynamic foragers."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0034_add_foragers"
down_revision = "0033_add_agent_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create `foragers` table for dynamic ingestion workers."""

    op.create_table(
        "foragers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default=sa.text("'rss'")),
        sa.Column("source_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("filter_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("prompt_template", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("tools", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("agent_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supervisor_routine_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_template_id"], ["agent_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supervisor_routine_id"], ["supervisor_routines.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_foragers_tenant_id", "foragers", ["tenant_id"], unique=False)
    op.create_index("ix_foragers_name", "foragers", ["name"], unique=False)
    op.create_index("ix_foragers_source_type", "foragers", ["source_type"], unique=False)


def downgrade() -> None:
    """Drop dynamic foragers table."""

    op.drop_index("ix_foragers_source_type", table_name="foragers")
    op.drop_index("ix_foragers_name", table_name="foragers")
    op.drop_index("ix_foragers_tenant_id", table_name="foragers")
    op.drop_table("foragers")
