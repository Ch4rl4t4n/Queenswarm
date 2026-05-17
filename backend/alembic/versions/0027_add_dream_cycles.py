"""Add dream cycle and dream insight persistence tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027"
down_revision = "0026_supervisor_sessions_tenant_hotfix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create dream cycle tables and indexes."""

    status_enum = sa.Enum("running", "completed", "failed", name="dream_cycle_status", native_enum=False, length=24)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "dream_cycles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", status_enum, nullable=False, server_default=sa.text("'running'")),
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("items_deduplicated", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("items_consolidated", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("digest_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("traceback_text", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dream_cycles_started_at", "dream_cycles", ["started_at"], unique=False)
    op.create_index("ix_dream_cycles_status", "dream_cycles", ["status"], unique=False)
    op.create_index("ix_dream_cycles_started_at_status", "dream_cycles", ["started_at", "status"], unique=False)

    op.create_table(
        "dream_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_kind", sa.String(length=80), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("neo4j_node_id", sa.String(length=160), nullable=True),
        sa.Column("chroma_doc_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["cycle_id"], ["dream_cycles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dream_insights_cycle_id", "dream_insights", ["cycle_id"], unique=False)
    op.create_index("ix_dream_insights_source_kind", "dream_insights", ["source_kind"], unique=False)
    op.create_index(
        "ix_dream_insights_source_kind_created_at",
        "dream_insights",
        ["source_kind", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop dream cycle tables and enum."""

    op.drop_index("ix_dream_insights_source_kind_created_at", table_name="dream_insights")
    op.drop_index("ix_dream_insights_source_kind", table_name="dream_insights")
    op.drop_index("ix_dream_insights_cycle_id", table_name="dream_insights")
    op.drop_table("dream_insights")

    op.drop_index("ix_dream_cycles_started_at_status", table_name="dream_cycles")
    op.drop_index("ix_dream_cycles_status", table_name="dream_cycles")
    op.drop_index("ix_dream_cycles_started_at", table_name="dream_cycles")
    op.drop_table("dream_cycles")

    status_enum = sa.Enum("running", "completed", "failed", name="dream_cycle_status", native_enum=False, length=24)
    status_enum.drop(op.get_bind(), checkfirst=True)
