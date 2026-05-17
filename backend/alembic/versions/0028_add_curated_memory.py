"""Add curated memory table for tenant Queen context files."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0028_add_curated_memory"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create curated memory table with uniqueness and size guardrail."""

    kind_enum = sa.Enum(
        "mission",
        "ideal_state",
        "soul",
        "skills_hierarchy",
        name="curated_file_kind",
        native_enum=False,
        length=32,
    )
    kind_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "curated_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", kind_enum, nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint("char_count <= 8000", name="ck_curated_memory_char_count_max"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["dashboard_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "kind", name="uq_curated_memory_tenant_kind"),
    )
    op.create_index("ix_curated_memory_tenant_id", "curated_memory", ["tenant_id"], unique=False)


def downgrade() -> None:
    """Drop curated memory table and enum."""

    op.drop_index("ix_curated_memory_tenant_id", table_name="curated_memory")
    op.drop_table("curated_memory")

    kind_enum = sa.Enum(
        "mission",
        "ideal_state",
        "soul",
        "skills_hierarchy",
        name="curated_file_kind",
        native_enum=False,
        length=32,
    )
    kind_enum.drop(op.get_bind(), checkfirst=True)
