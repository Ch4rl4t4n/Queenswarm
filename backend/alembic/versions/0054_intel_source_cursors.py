"""Social intel scrape watermarks."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0054_intel_source_cursors"
down_revision = "0053_commerce_order_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create intel_source_cursors for YouTube/X delta scraping."""

    op.create_table(
        "intel_source_cursors",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("forager_id", UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("last_external_id", sa.String(length=255), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backfill_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["forager_id"], ["foragers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "forager_id",
            "platform",
            "source_key",
            name="uq_intel_source_cursors_forager_source",
        ),
    )
    op.create_index("ix_intel_source_cursors_tenant_id", "intel_source_cursors", ["tenant_id"])
    op.create_index("ix_intel_source_cursors_forager_id", "intel_source_cursors", ["forager_id"])


def downgrade() -> None:
    """Drop intel source cursor table."""

    op.drop_index("ix_intel_source_cursors_forager_id", table_name="intel_source_cursors")
    op.drop_index("ix_intel_source_cursors_tenant_id", table_name="intel_source_cursors")
    op.drop_table("intel_source_cursors")
