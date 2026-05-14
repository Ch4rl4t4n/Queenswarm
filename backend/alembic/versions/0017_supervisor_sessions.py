"""Dynamic supervisor sessions + sub-agent timelines."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017_supervisor_sessions"
down_revision = "0016_pgvector_hive_vectors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create additive tables for supervisor sessions and event logs."""

    op.create_table(
        "supervisor_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("runtime_mode", sa.String(length=16), nullable=False, server_default="inprocess"),
        sa.Column("created_by_subject", sa.String(length=512), nullable=True),
        sa.Column(
            "context_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("swarm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["swarm_id"],
            ["sub_swarms.id"],
            name="fk_supervisor_sessions_swarm_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_supervisor_sessions_task_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supervisor_sessions_status",
        "supervisor_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_supervisor_sessions_created_by_subject",
        "supervisor_sessions",
        ["created_by_subject"],
        unique=False,
    )

    op.create_table(
        "sub_agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("supervisor_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("runtime_mode", sa.String(length=16), nullable=False, server_default="inprocess"),
        sa.Column(
            "toolset",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "short_memory",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("spawn_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_output", sa.Text(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["supervisor_session_id"],
            ["supervisor_sessions.id"],
            name="fk_sub_agent_sessions_supervisor_session_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sub_agent_sessions_supervisor_session_id",
        "sub_agent_sessions",
        ["supervisor_session_id"],
        unique=False,
    )
    op.create_index("ix_sub_agent_sessions_role", "sub_agent_sessions", ["role"], unique=False)
    op.create_index("ix_sub_agent_sessions_status", "sub_agent_sessions", ["status"], unique=False)

    op.create_table(
        "supervisor_session_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("supervisor_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sub_agent_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["supervisor_session_id"],
            ["supervisor_sessions.id"],
            name="fk_supervisor_session_events_supervisor_session_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sub_agent_session_id"],
            ["sub_agent_sessions.id"],
            name="fk_supervisor_session_events_sub_agent_session_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supervisor_session_events_supervisor_session_id",
        "supervisor_session_events",
        ["supervisor_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_supervisor_session_events_sub_agent_session_id",
        "supervisor_session_events",
        ["sub_agent_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_supervisor_session_events_event_type",
        "supervisor_session_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_supervisor_session_events_occurred_at",
        "supervisor_session_events",
        ["occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop supervisor session tables in reverse dependency order."""

    op.drop_index("ix_supervisor_session_events_occurred_at", table_name="supervisor_session_events")
    op.drop_index("ix_supervisor_session_events_event_type", table_name="supervisor_session_events")
    op.drop_index("ix_supervisor_session_events_sub_agent_session_id", table_name="supervisor_session_events")
    op.drop_index("ix_supervisor_session_events_supervisor_session_id", table_name="supervisor_session_events")
    op.drop_table("supervisor_session_events")
    op.drop_index("ix_sub_agent_sessions_status", table_name="sub_agent_sessions")
    op.drop_index("ix_sub_agent_sessions_role", table_name="sub_agent_sessions")
    op.drop_index("ix_sub_agent_sessions_supervisor_session_id", table_name="sub_agent_sessions")
    op.drop_table("sub_agent_sessions")
    op.drop_index("ix_supervisor_sessions_created_by_subject", table_name="supervisor_sessions")
    op.drop_index("ix_supervisor_sessions_status", table_name="supervisor_sessions")
    op.drop_table("supervisor_sessions")

