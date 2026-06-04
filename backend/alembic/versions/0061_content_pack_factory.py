"""Content Pack Factory — tenant publish packs + market opportunities queue."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0061_content_pack_factory"
down_revision = "0060_skill_factory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_content_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("channel", sa.String(32), nullable=False, server_default="instagram"),
        sa.Column("pack_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("listing_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("keywords", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source", sa.String(32), nullable=False, server_default="factory"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gumroad_exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_tenant_content_packs_tenant_slug"),
    )
    op.create_index("ix_tenant_content_packs_tenant_active", "tenant_content_packs", ["tenant_id", "is_active"])

    op.create_table(
        "content_pack_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("niche", sa.String(200), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("demand_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("competition_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("buildability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("composite_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("suggested_price_eur_cents", sa.Integer(), nullable=False, server_default="1900"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("supervisor_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_content_pack_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant_content_packs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_content_pack_opportunities_tenant_status", "content_pack_opportunities", ["tenant_id", "status"])
    op.create_index("ix_content_pack_opportunities_composite", "content_pack_opportunities", ["tenant_id", "composite_score"])


def downgrade() -> None:
    op.drop_index("ix_content_pack_opportunities_composite", table_name="content_pack_opportunities")
    op.drop_index("ix_content_pack_opportunities_tenant_status", table_name="content_pack_opportunities")
    op.drop_table("content_pack_opportunities")
    op.drop_index("ix_tenant_content_packs_tenant_active", table_name="tenant_content_packs")
    op.drop_table("tenant_content_packs")
