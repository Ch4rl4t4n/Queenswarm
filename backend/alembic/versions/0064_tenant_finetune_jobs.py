"""Tenant fine-tune job queue — Track M LOC9."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0064_tenant_finetune_jobs"
down_revision = "0063_tenant_local_adapters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_finetune_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_approval"),
        sa.Column("adapter_name", sa.String(64), nullable=False),
        sa.Column("base_model", sa.String(128), nullable=False),
        sa.Column("dataset_source", sa.String(32), nullable=False),
        sa.Column("dataset_path", sa.Text(), nullable=True),
        sa.Column("dataset_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("epochs", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approved_by_subject", sa.String(256), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "training_plan_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_tenant_finetune_jobs_tenant_status",
        "tenant_finetune_jobs",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_finetune_jobs_tenant_status", table_name="tenant_finetune_jobs")
    op.drop_table("tenant_finetune_jobs")
