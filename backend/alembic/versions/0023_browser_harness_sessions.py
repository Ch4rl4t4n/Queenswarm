"""Phase 12.1 — browser harness sessions and action logs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023_browser_harness_sessions"
down_revision = "0022_agent_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "browser_automation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("supervisor_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sub_agent_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_subject", sa.String(length=512), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("start_url", sa.String(length=2048), nullable=True),
        sa.Column("current_url", sa.String(length=2048), nullable=True),
        sa.Column("allowed_domains", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("blocked_reason", sa.String(length=800), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_actions", sa.Integer(), nullable=False),
        sa.Column("actions_used", sa.Integer(), nullable=False),
        sa.Column("pending_approval_action", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("last_snapshot_text", sa.Text(), nullable=True),
        sa.Column("last_screenshot_base64", sa.Text(), nullable=True),
        sa.Column("is_headless", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supervisor_session_id"], ["supervisor_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sub_agent_session_id"], ["sub_agent_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_browser_automation_sessions_tenant_id", "browser_automation_sessions", ["tenant_id"], unique=False)
    op.create_index("ix_browser_automation_sessions_supervisor_session_id", "browser_automation_sessions", ["supervisor_session_id"], unique=False)
    op.create_index("ix_browser_automation_sessions_sub_agent_session_id", "browser_automation_sessions", ["sub_agent_session_id"], unique=False)
    op.create_index("ix_browser_automation_sessions_mode", "browser_automation_sessions", ["mode"], unique=False)
    op.create_index("ix_browser_automation_sessions_status", "browser_automation_sessions", ["status"], unique=False)

    op.create_table(
        "browser_automation_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("browser_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("result_summary", sa.String(length=2000), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["browser_session_id"], ["browser_automation_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_browser_automation_actions_tenant_id", "browser_automation_actions", ["tenant_id"], unique=False)
    op.create_index("ix_browser_automation_actions_browser_session_id", "browser_automation_actions", ["browser_session_id"], unique=False)
    op.create_index("ix_browser_automation_actions_action_type", "browser_automation_actions", ["action_type"], unique=False)
    op.create_index("ix_browser_automation_actions_status", "browser_automation_actions", ["status"], unique=False)
    op.create_index("ix_browser_automation_actions_occurred_at", "browser_automation_actions", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_browser_automation_actions_occurred_at", table_name="browser_automation_actions")
    op.drop_index("ix_browser_automation_actions_status", table_name="browser_automation_actions")
    op.drop_index("ix_browser_automation_actions_action_type", table_name="browser_automation_actions")
    op.drop_index("ix_browser_automation_actions_browser_session_id", table_name="browser_automation_actions")
    op.drop_index("ix_browser_automation_actions_tenant_id", table_name="browser_automation_actions")
    op.drop_table("browser_automation_actions")

    op.drop_index("ix_browser_automation_sessions_status", table_name="browser_automation_sessions")
    op.drop_index("ix_browser_automation_sessions_mode", table_name="browser_automation_sessions")
    op.drop_index("ix_browser_automation_sessions_sub_agent_session_id", table_name="browser_automation_sessions")
    op.drop_index("ix_browser_automation_sessions_supervisor_session_id", table_name="browser_automation_sessions")
    op.drop_index("ix_browser_automation_sessions_tenant_id", table_name="browser_automation_sessions")
    op.drop_table("browser_automation_sessions")
