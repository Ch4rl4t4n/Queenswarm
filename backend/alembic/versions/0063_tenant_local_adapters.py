"""Tenant local adapter registry — Track M LOC8."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0063_tenant_local_adapters"
down_revision = "0062_skill_picker_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_local_adapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("ollama_tag", sa.String(64), nullable=False),
        sa.Column("litellm_slug", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False, server_default="gguf"),
        sa.Column("base_model", sa.String(128), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "ollama_tag", name="uq_tenant_local_adapters_tenant_tag"),
    )
    op.create_index(
        "ix_tenant_local_adapters_tenant_active",
        "tenant_local_adapters",
        ["tenant_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_local_adapters_tenant_active", table_name="tenant_local_adapters")
    op.drop_table("tenant_local_adapters")
