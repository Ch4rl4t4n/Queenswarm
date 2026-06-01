"""Add mission-kanban task statuses: triage, ready, blocked."""

from __future__ import annotations

from alembic import op

revision = "0056_mission_kanban_task_statuses"
down_revision = "0055_curated_memory_char_limit_24k"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend tasks.status check constraint for Hermes-style mission kanban columns."""

    op.execute(
        """
        ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
        """
    )
    op.execute(
        """
        ALTER TABLE tasks ADD CONSTRAINT tasks_status_check CHECK (
            status IN (
                'triage', 'pending', 'ready', 'running', 'blocked',
                'completed', 'failed', 'cancelled'
            )
        );
        """
    )


def downgrade() -> None:
    """Revert to legacy status set — map new values back to pending."""

    op.execute(
        """
        UPDATE tasks SET status = 'pending'
        WHERE status IN ('triage', 'ready', 'blocked');
        """
    )
    op.execute(
        """
        ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
        """
    )
    op.execute(
        """
        ALTER TABLE tasks ADD CONSTRAINT tasks_status_check CHECK (
            status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
        );
        """
    )
