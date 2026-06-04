"""Skill picker usage tallies — backend favorites instead of localStorage."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0062_skill_picker_usage"
down_revision = "0061_content_pack_factory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_skill_picker_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("skill_slug", sa.String(120), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "skill_slug", name="uq_tenant_skill_picker_usage_tenant_slug"),
    )
    op.create_index(
        "ix_tenant_skill_picker_usage_tenant_count",
        "tenant_skill_picker_usage",
        ["tenant_id", "usage_count"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_skill_picker_usage_tenant_count", table_name="tenant_skill_picker_usage")
    op.drop_table("tenant_skill_picker_usage")
