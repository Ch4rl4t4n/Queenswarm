"""Add hive_async_workflow_runs audit ledger for Celery-deferred swarm runs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002_hive_async_workflow_runs"
down_revision = "0001_initial_bee_hive"
branch_labels = None
depends_on = None

UUID = pg.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "hive_async_workflow_runs",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("celery_task_id", sa.String(length=96), nullable=False),
        sa.Column("swarm_id", UUID, nullable=False),
        sa.Column("workflow_id", UUID, nullable=False),
        sa.Column("hive_task_id", UUID, nullable=True),
        sa.Column("requested_by_subject", sa.String(length=512), nullable=True),
        sa.Column("lifecycle", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("result_snapshot", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["hive_task_id"],
            ["tasks.id"],
            name="fk_hive_async_workflow_runs_hive_task_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["swarm_id"],
            ["sub_swarms.id"],
            name="fk_hive_async_workflow_runs_swarm_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            name="fk_hive_async_workflow_runs_workflow_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("celery_task_id", name="uq_hive_async_workflow_runs_celery_task_id"),
    )
    op.create_index(
        "ix_hive_async_workflow_runs_celery_task_id",
        "hive_async_workflow_runs",
        ["celery_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hive_async_workflow_runs_celery_task_id", table_name="hive_async_workflow_runs")
    op.drop_table("hive_async_workflow_runs")
