"""Enable pg_trgm GIN indexes for fast mission search (OW16)."""

from __future__ import annotations

from alembic import op

revision = "0057_mission_search_trgm_indexes"
down_revision = "0056_mission_kanban_task_statuses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add trigram indexes for supervisor goals, task titles, and sub-agent output."""

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_supervisor_sessions_goal_trgm
        ON supervisor_sessions USING gin (goal gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tasks_title_trgm
        ON tasks USING gin (title gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_sub_agent_sessions_last_output_trgm
        ON sub_agent_sessions USING gin (last_output gin_trgm_ops)
        """
    )


def downgrade() -> None:
    """Drop mission search trigram indexes."""

    op.execute("DROP INDEX IF EXISTS ix_sub_agent_sessions_last_output_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tasks_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_supervisor_sessions_goal_trgm")
