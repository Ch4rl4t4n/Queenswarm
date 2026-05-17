"""Task final deliverables archive (Phase 0.51)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_task_final_deliverables"
down_revision = "0012_connector_vault_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_final_deliverables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("lineage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("dashboard_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ballroom_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("markdown_body", sa.Text(), nullable=False),
        sa.Column("structured_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("voice_script", sa.Text(), nullable=True),
        sa.Column("chroma_embedding_id", sa.String(length=160), nullable=True),
        sa.Column("archive_relpath", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["dashboard_user_id"], ["dashboard_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lineage_id", "version", name="uq_deliverable_lineage_version"),
    )
    op.create_index("ix_task_final_deliverables_lineage_created", "task_final_deliverables", ["lineage_id", "created_at"])
    op.create_index(
        "ix_task_final_deliverables_user_created",
        "task_final_deliverables",
        ["dashboard_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_task_final_deliverables_user_created", table_name="task_final_deliverables")
    op.drop_index("ix_task_final_deliverables_lineage_created", table_name="task_final_deliverables")
    op.drop_table("task_final_deliverables")
