"""Add Grok Control Plane persistent run ledger."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0050_grok_control_plane"
down_revision = "0049_social_connected_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grok_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "dashboard_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("dashboard_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("scope_paths", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("run_mode", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("command_profile", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approved_by", sa.String(length=256), nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_grok_runs_tenant_status", "grok_runs", ["tenant_id", "status"])
    op.create_index("ix_grok_runs_tenant_created_at", "grok_runs", ["tenant_id", "created_at"])

    op.create_table(
        "grok_run_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("grok_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("run_id", "step_order", name="uq_grok_run_steps_order"),
    )
    op.create_index("ix_grok_run_steps_run_id", "grok_run_steps", ["run_id"])
    op.create_index("ix_grok_run_steps_tenant_status", "grok_run_steps", ["tenant_id", "status"])

    op.create_table(
        "grok_run_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("grok_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_grok_run_events_run_occurred_at", "grok_run_events", ["run_id", "occurred_at"])

    op.create_table(
        "grok_run_approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("grok_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("decided_by", sa.String(length=256), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_grok_run_approvals_run_decided_at", "grok_run_approvals", ["run_id", "decided_at"])

    op.create_table(
        "grok_run_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("grok_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False, server_default="text/plain"),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("artifact_meta", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_grok_run_artifacts_run_kind", "grok_run_artifacts", ["run_id", "artifact_kind"])


def downgrade() -> None:
    op.drop_index("ix_grok_run_artifacts_run_kind", table_name="grok_run_artifacts")
    op.drop_table("grok_run_artifacts")

    op.drop_index("ix_grok_run_approvals_run_decided_at", table_name="grok_run_approvals")
    op.drop_table("grok_run_approvals")

    op.drop_index("ix_grok_run_events_run_occurred_at", table_name="grok_run_events")
    op.drop_table("grok_run_events")

    op.drop_index("ix_grok_run_steps_tenant_status", table_name="grok_run_steps")
    op.drop_index("ix_grok_run_steps_run_id", table_name="grok_run_steps")
    op.drop_table("grok_run_steps")

    op.drop_index("ix_grok_runs_tenant_created_at", table_name="grok_runs")
    op.drop_index("ix_grok_runs_tenant_status", table_name="grok_runs")
    op.drop_table("grok_runs")
