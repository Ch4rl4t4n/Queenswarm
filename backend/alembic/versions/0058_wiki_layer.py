"""Wiki Layer — compiled pages + gardener run audit (Karpathy-style hot/cold tier)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0058_wiki_layer"
down_revision = "0057_mission_search_trgm_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create wiki_layer_pages and wiki_gardener_runs tables."""

    op.create_table(
        "wiki_layer_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=96), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False, server_default=sa.text("''")),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "source_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_wiki_layer_pages_tenant_slug"),
    )
    op.create_index("ix_wiki_layer_pages_tenant_id", "wiki_layer_pages", ["tenant_id"], unique=False)

    op.create_table(
        "wiki_gardener_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'running'")),
        sa.Column("summary_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("pages_updated", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("raw_scanned", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("pollen_awarded", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wiki_gardener_runs_tenant_id", "wiki_gardener_runs", ["tenant_id"], unique=False)
    op.create_index("ix_wiki_gardener_runs_status", "wiki_gardener_runs", ["status"], unique=False)


def downgrade() -> None:
    """Drop wiki layer tables."""

    op.drop_index("ix_wiki_gardener_runs_status", table_name="wiki_gardener_runs")
    op.drop_index("ix_wiki_gardener_runs_tenant_id", table_name="wiki_gardener_runs")
    op.drop_table("wiki_gardener_runs")
    op.drop_index("ix_wiki_layer_pages_tenant_id", table_name="wiki_layer_pages")
    op.drop_table("wiki_layer_pages")
