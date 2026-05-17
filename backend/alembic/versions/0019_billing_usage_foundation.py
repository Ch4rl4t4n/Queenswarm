"""Phase 10.3 — billing foundation and tenant-scoped cost usage."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_billing_usage_foundation"
down_revision = "0017_rbac_team_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cost_records", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_cost_records_tenant_id_tenants",
        "cost_records",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_cost_records_tenant_id", "cost_records", ["tenant_id"], unique=False)

    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("billing_cycle_anchor", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "limits_override",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "feature_overrides",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant_id"),
    )
    op.create_index("ix_tenant_subscriptions_tenant_id", "tenant_subscriptions", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_subscriptions_tier", "tenant_subscriptions", ["tier"], unique=False)
    op.create_index("ix_tenant_subscriptions_status", "tenant_subscriptions", ["status"], unique=False)
    op.create_index("ix_tenant_subscriptions_stripe_customer_id", "tenant_subscriptions", ["stripe_customer_id"], unique=False)
    op.create_index(
        "ix_tenant_subscriptions_stripe_subscription_id",
        "tenant_subscriptions",
        ["stripe_subscription_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_subscriptions_stripe_subscription_id", table_name="tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_stripe_customer_id", table_name="tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_status", table_name="tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_tier", table_name="tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_tenant_id", table_name="tenant_subscriptions")
    op.drop_table("tenant_subscriptions")

    op.drop_index("ix_cost_records_tenant_id", table_name="cost_records")
    op.drop_constraint("fk_cost_records_tenant_id_tenants", "cost_records", type_="foreignkey")
    op.drop_column("cost_records", "tenant_id")
