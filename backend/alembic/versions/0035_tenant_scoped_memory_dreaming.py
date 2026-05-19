"""Tenant-scope dream cycles and add report payloads."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0035_tenant_scoped_memory_dreaming"
down_revision = "0034_add_foragers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tenant scoping + JSON dream report fields for dreaming tables."""

    op.add_column(
        "dream_cycles",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "dream_cycles",
        sa.Column("dream_report", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_dream_cycles_tenant_id", "dream_cycles", ["tenant_id"], unique=False)
    op.create_index("ix_dream_cycles_tenant_started_at", "dream_cycles", ["tenant_id", "started_at"], unique=False)

    op.add_column(
        "dream_insights",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_dream_insights_tenant_id", "dream_insights", ["tenant_id"], unique=False)
    op.create_index("ix_dream_insights_tenant_created_at", "dream_insights", ["tenant_id", "created_at"], unique=False)


def downgrade() -> None:
    """Remove tenant scoping + report payload fields from dreaming tables."""

    op.drop_index("ix_dream_insights_tenant_created_at", table_name="dream_insights")
    op.drop_index("ix_dream_insights_tenant_id", table_name="dream_insights")
    op.drop_column("dream_insights", "tenant_id")

    op.drop_index("ix_dream_cycles_tenant_started_at", table_name="dream_cycles")
    op.drop_index("ix_dream_cycles_tenant_id", table_name="dream_cycles")
    op.drop_column("dream_cycles", "dream_report")
    op.drop_column("dream_cycles", "tenant_id")
