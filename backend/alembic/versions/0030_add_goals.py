"""Add goal orchestration tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0030_add_goals"
down_revision = "0029_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create goals and goal audit history tables."""

    goal_status_enum = sa.Enum(
        "pending",
        "decomposing",
        "executing",
        "auditing",
        "completed",
        "failed",
        "halted_by_budget",
        "halted_by_human",
        name="goal_status",
        native_enum=False,
        length=32,
    )
    goal_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("acceptance_criteria_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("budget_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", goal_status_enum, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("current_iteration", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("root_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("halt_reason", sa.Text(), nullable=True),
        sa.Column("spent_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["dashboard_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goals_tenant_id", "goals", ["tenant_id"], unique=False)
    op.create_index("ix_goals_user_id", "goals", ["user_id"], unique=False)
    op.create_index("ix_goals_status", "goals", ["status"], unique=False)
    op.create_index("ix_goals_root_task_id", "goals", ["root_task_id"], unique=False)

    op.create_table(
        "goal_audit_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reasoning", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("remaining_work_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goal_audit_results_goal_id", "goal_audit_results", ["goal_id"], unique=False)
    op.create_index("ix_goal_audit_results_tenant_id", "goal_audit_results", ["tenant_id"], unique=False)


def downgrade() -> None:
    """Drop goals tables and enum."""

    op.drop_index("ix_goal_audit_results_tenant_id", table_name="goal_audit_results")
    op.drop_index("ix_goal_audit_results_goal_id", table_name="goal_audit_results")
    op.drop_table("goal_audit_results")

    op.drop_index("ix_goals_root_task_id", table_name="goals")
    op.drop_index("ix_goals_status", table_name="goals")
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_index("ix_goals_tenant_id", table_name="goals")
    op.drop_table("goals")

    goal_status_enum = sa.Enum(
        "pending",
        "decomposing",
        "executing",
        "auditing",
        "completed",
        "failed",
        "halted_by_budget",
        "halted_by_human",
        name="goal_status",
        native_enum=False,
        length=32,
    )
    goal_status_enum.drop(op.get_bind(), checkfirst=True)
