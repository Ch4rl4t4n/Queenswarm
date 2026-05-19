"""Alembic migration: operator pending-review queue."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0038_pending_review_queue"
down_revision = "0037_paper_trading_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_review_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("swarm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("simulation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("confidence_fraction", sa.Float(), nullable=True),
        sa.Column("verification_passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("step_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=128), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["swarm_id"], ["sub_swarms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pending_review_items_status_created",
        "pending_review_items",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index("ix_pending_review_items_swarm_id", "pending_review_items", ["swarm_id"], unique=False)
    op.create_index("ix_pending_review_items_task_id", "pending_review_items", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pending_review_items_task_id", table_name="pending_review_items")
    op.drop_index("ix_pending_review_items_swarm_id", table_name="pending_review_items")
    op.drop_index("ix_pending_review_items_status_created", table_name="pending_review_items")
    op.drop_table("pending_review_items")
