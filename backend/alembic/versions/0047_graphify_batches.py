"""Add graphify_batches for Phase 4 Auto-Graphify folder ingest."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0047_graphify_batches"
down_revision = "0046_dump_sleep_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create graphify_batches table."""

    op.create_table(
        "graphify_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_subject", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("folder_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("graph_nodes_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vectors_embedded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pollen_earned", sa.Float(), nullable=False, server_default="0"),
        sa.Column("summary_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("vault_rel_path", sa.String(length=512), nullable=True),
        sa.Column(
            "storage_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graphify_batches_tenant_id", "graphify_batches", ["tenant_id"], unique=False)
    op.create_index("ix_graphify_batches_status", "graphify_batches", ["status"], unique=False)
    op.create_index(
        "ix_graphify_batches_tenant_created_at",
        "graphify_batches",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop graphify_batches table."""

    op.drop_index("ix_graphify_batches_tenant_created_at", table_name="graphify_batches")
    op.drop_index("ix_graphify_batches_status", table_name="graphify_batches")
    op.drop_index("ix_graphify_batches_tenant_id", table_name="graphify_batches")
    op.drop_table("graphify_batches")
