"""Generic external orchestrator pull feed table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_external_outputs"
down_revision = "0006_seed_orchestrator"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store immutable orchestrator delivery rows keyed by dashboard user."""

    op.create_table(
        "external_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "dashboard_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("text_report", sa.Text(), nullable=False),
        sa.Column("voice_script", sa.Text(), nullable=True),
        sa.Column(
            "output_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("simulation_outcome", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=128)),
            server_default=sa.text("ARRAY[]::varchar[]"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dashboard_user_id"], ["dashboard_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_outputs_dashboard_user_created",
        "external_outputs",
        ["dashboard_user_id", "created_at"],
    )


def downgrade() -> None:
    """Drop generic feed."""

    op.drop_index("ix_external_outputs_dashboard_user_created", table_name="external_outputs")
    op.drop_table("external_outputs")
