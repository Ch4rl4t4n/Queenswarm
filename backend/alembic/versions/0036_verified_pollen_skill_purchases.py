"""Verified pollen flag on rewards + skill purchase ledger for Stripe checkout."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0036_verified_pollen_skill_purchases"
down_revision = "0035_tenant_scoped_memory_dreaming"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pollen_rewards",
        sa.Column("verified_reward", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_pollen_rewards_verified_reward",
        "pollen_rewards",
        ["verified_reward"],
        unique=False,
    )

    op.create_table(
        "skill_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dashboard_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="eur"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "recipe_id",
            name="uq_skill_purchases_tenant_recipe",
        ),
    )
    op.create_index("ix_skill_purchases_tenant_id", "skill_purchases", ["tenant_id"], unique=False)
    op.create_index("ix_skill_purchases_recipe_id", "skill_purchases", ["recipe_id"], unique=False)
    op.create_index(
        "ix_skill_purchases_stripe_checkout_session_id",
        "skill_purchases",
        ["stripe_checkout_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_skill_purchases_stripe_checkout_session_id", table_name="skill_purchases")
    op.drop_index("ix_skill_purchases_recipe_id", table_name="skill_purchases")
    op.drop_index("ix_skill_purchases_tenant_id", table_name="skill_purchases")
    op.drop_table("skill_purchases")
    op.drop_index("ix_pollen_rewards_verified_reward", table_name="pollen_rewards")
    op.drop_column("pollen_rewards", "verified_reward")
