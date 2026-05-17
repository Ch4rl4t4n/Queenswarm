"""Phase 11.3 — agent initiative suggestions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022_agent_suggestions"
down_revision = "0021_memory_evolution_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("supervisor_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sub_agent_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposal_type", sa.String(length=48), nullable=False),
        sa.Column("proposed_by_role", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=260), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "proposal_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("impact_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("requires_manual_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evaluation_reason", sa.String(length=800), nullable=True),
        sa.Column("reviewed_by_subject", sa.String(length=512), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supervisor_session_id"], ["supervisor_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sub_agent_session_id"], ["sub_agent_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_suggestions_tenant_id", "agent_suggestions", ["tenant_id"], unique=False)
    op.create_index("ix_agent_suggestions_supervisor_session_id", "agent_suggestions", ["supervisor_session_id"], unique=False)
    op.create_index("ix_agent_suggestions_sub_agent_session_id", "agent_suggestions", ["sub_agent_session_id"], unique=False)
    op.create_index("ix_agent_suggestions_proposal_type", "agent_suggestions", ["proposal_type"], unique=False)
    op.create_index("ix_agent_suggestions_proposed_by_role", "agent_suggestions", ["proposed_by_role"], unique=False)
    op.create_index("ix_agent_suggestions_risk_level", "agent_suggestions", ["risk_level"], unique=False)
    op.create_index("ix_agent_suggestions_status", "agent_suggestions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_suggestions_status", table_name="agent_suggestions")
    op.drop_index("ix_agent_suggestions_risk_level", table_name="agent_suggestions")
    op.drop_index("ix_agent_suggestions_proposed_by_role", table_name="agent_suggestions")
    op.drop_index("ix_agent_suggestions_proposal_type", table_name="agent_suggestions")
    op.drop_index("ix_agent_suggestions_sub_agent_session_id", table_name="agent_suggestions")
    op.drop_index("ix_agent_suggestions_supervisor_session_id", table_name="agent_suggestions")
    op.drop_index("ix_agent_suggestions_tenant_id", table_name="agent_suggestions")
    op.drop_table("agent_suggestions")
