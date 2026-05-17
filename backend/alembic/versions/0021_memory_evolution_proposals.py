"""Phase 11.2 — memory evolution proposals."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021_memory_evolution_proposals"
down_revision = "0020_public_sharing_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_evolution_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("proposal_kind", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.String(length=2000), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("requires_manual_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("proposed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proposed_by_user_id"], ["dashboard_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["dashboard_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memory_evolution_proposals_tenant_id",
        "memory_evolution_proposals",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_memory_evolution_proposals_proposal_kind",
        "memory_evolution_proposals",
        ["proposal_kind"],
        unique=False,
    )
    op.create_index(
        "ix_memory_evolution_proposals_status",
        "memory_evolution_proposals",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_memory_evolution_proposals_proposed_by_user_id",
        "memory_evolution_proposals",
        ["proposed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_memory_evolution_proposals_approved_by_user_id",
        "memory_evolution_proposals",
        ["approved_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memory_evolution_proposals_approved_by_user_id", table_name="memory_evolution_proposals")
    op.drop_index("ix_memory_evolution_proposals_proposed_by_user_id", table_name="memory_evolution_proposals")
    op.drop_index("ix_memory_evolution_proposals_status", table_name="memory_evolution_proposals")
    op.drop_index("ix_memory_evolution_proposals_proposal_kind", table_name="memory_evolution_proposals")
    op.drop_index("ix_memory_evolution_proposals_tenant_id", table_name="memory_evolution_proposals")
    op.drop_table("memory_evolution_proposals")
