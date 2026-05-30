"""Commerce order events — Postgres audit retention."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0053_commerce_order_events"
down_revision = "0052_grok_templates_and_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commerce_order_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("firm_id", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("object_id", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("customer_id", sa.String(length=255), nullable=True),
        sa.Column("order_status", sa.String(length=64), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "event_id", name="uq_commerce_order_events_provider_event_id"),
    )
    op.create_index("ix_commerce_order_events_tenant_ingested", "commerce_order_events", ["tenant_id", "ingested_at"])
    op.create_index("ix_commerce_order_events_firm_ingested", "commerce_order_events", ["firm_id", "ingested_at"])
    op.create_index("ix_commerce_order_events_provider", "commerce_order_events", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_commerce_order_events_provider", table_name="commerce_order_events")
    op.drop_index("ix_commerce_order_events_firm_ingested", table_name="commerce_order_events")
    op.drop_index("ix_commerce_order_events_tenant_ingested", table_name="commerce_order_events")
    op.drop_table("commerce_order_events")
