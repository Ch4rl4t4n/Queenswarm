"""Add lightweight scheduled routines for supervisor sessions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018_supervisor_routines"
down_revision = "0017_supervisor_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create additive ``supervisor_routines`` table."""

    op.create_table(
        "supervisor_routines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("goal_template", sa.Text(), nullable=False),
        sa.Column("schedule_kind", sa.String(length=16), nullable=False, server_default="interval"),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("cron_expr", sa.String(length=64), nullable=True),
        sa.Column("runtime_mode", sa.String(length=16), nullable=False, server_default="durable"),
        sa.Column(
            "roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("retrieval_contract", sa.String(length=200), nullable=True),
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "context_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="idle"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_subject", sa.String(length=512), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supervisor_routines_name", "supervisor_routines", ["name"], unique=False)
    op.create_index("ix_supervisor_routines_is_active", "supervisor_routines", ["is_active"], unique=False)
    op.create_index("ix_supervisor_routines_next_run_at", "supervisor_routines", ["next_run_at"], unique=False)
    op.create_index(
        "ix_supervisor_routines_created_by_subject",
        "supervisor_routines",
        ["created_by_subject"],
        unique=False,
    )


def downgrade() -> None:
    """Drop ``supervisor_routines`` table."""

    op.drop_index("ix_supervisor_routines_created_by_subject", table_name="supervisor_routines")
    op.drop_index("ix_supervisor_routines_next_run_at", table_name="supervisor_routines")
    op.drop_index("ix_supervisor_routines_is_active", table_name="supervisor_routines")
    op.drop_index("ix_supervisor_routines_name", table_name="supervisor_routines")
    op.drop_table("supervisor_routines")
