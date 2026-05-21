"""Add dump_sleep_batches for Phase 4 overnight ingest queue."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0046_dump_sleep_batches"
down_revision = "0045_skill_marketplace_ugc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create dump_sleep_batches table."""

    op.create_table(
        "dump_sleep_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_subject", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("voice_note_text", sa.Text(), nullable=True),
        sa.Column("items_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stalled_signals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pollen_earned", sa.Float(), nullable=False, server_default="0"),
        sa.Column("briefing_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("dream_cycle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "storage_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["dream_cycle_id"], ["dream_cycles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dump_sleep_batches_tenant_id", "dump_sleep_batches", ["tenant_id"], unique=False)
    op.create_index("ix_dump_sleep_batches_status", "dump_sleep_batches", ["status"], unique=False)
    op.create_index(
        "ix_dump_sleep_batches_tenant_created_at",
        "dump_sleep_batches",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop dump_sleep_batches table."""

    op.drop_index("ix_dump_sleep_batches_tenant_created_at", table_name="dump_sleep_batches")
    op.drop_index("ix_dump_sleep_batches_status", table_name="dump_sleep_batches")
    op.drop_index("ix_dump_sleep_batches_tenant_id", table_name="dump_sleep_batches")
    op.drop_table("dump_sleep_batches")
