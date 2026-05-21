"""Add skill_marketplace_listings + purchase fee columns for UGC revenue split."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0045_skill_marketplace_ugc"
down_revision = "0044_tenant_operator_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "skill_marketplace_listings" not in tables:
        op.create_table(
            "skill_marketplace_listings",
            sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("publisher_tenant_id", PG_UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("publisher_user_id", PG_UUID(as_uuid=True), nullable=False),
            sa.Column("recipe_id", PG_UUID(as_uuid=True), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
            sa.Column("price_eur_cents", sa.Integer(), nullable=False),
            sa.Column("platform_cut_bps", sa.Integer(), nullable=False, server_default="2500"),
            sa.Column("pitch", sa.Text(), nullable=True),
            sa.Column("curator_note", sa.Text(), nullable=True),
            sa.Column("reviewer_user_id", PG_UUID(as_uuid=True), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("recipe_id", name="uq_skill_marketplace_listings_recipe"),
        )
        op.create_index("ix_skill_marketplace_listings_publisher_tenant_id", "skill_marketplace_listings", ["publisher_tenant_id"])
        op.create_index("ix_skill_marketplace_listings_recipe_id", "skill_marketplace_listings", ["recipe_id"])
        op.create_index("ix_skill_marketplace_listings_status", "skill_marketplace_listings", ["status"])

    purchase_cols = {col["name"] for col in inspector.get_columns("skill_purchases")}
    if "marketplace_listing_id" not in purchase_cols:
        op.add_column(
            "skill_purchases",
            sa.Column("marketplace_listing_id", PG_UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_skill_purchases_marketplace_listing_id",
            "skill_purchases",
            "skill_marketplace_listings",
            ["marketplace_listing_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "platform_fee_cents" not in purchase_cols:
        op.add_column(
            "skill_purchases",
            sa.Column("platform_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        )
    if "publisher_tenant_id" not in purchase_cols:
        op.add_column(
            "skill_purchases",
            sa.Column("publisher_tenant_id", PG_UUID(as_uuid=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    purchase_cols = {col["name"] for col in inspector.get_columns("skill_purchases")}
    if "publisher_tenant_id" in purchase_cols:
        op.drop_column("skill_purchases", "publisher_tenant_id")
    if "platform_fee_cents" in purchase_cols:
        op.drop_column("skill_purchases", "platform_fee_cents")
    if "marketplace_listing_id" in purchase_cols:
        op.drop_constraint("fk_skill_purchases_marketplace_listing_id", "skill_purchases", type_="foreignkey")
        op.drop_column("skill_purchases", "marketplace_listing_id")
    if "skill_marketplace_listings" in inspector.get_table_names():
        op.drop_table("skill_marketplace_listings")
