"""Composite indexes for solo operator list/query hot paths."""

from __future__ import annotations

from alembic import op

revision = "0048_solo_perf_indexes"
down_revision = "0047_graphify_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tasks_tenant_status_created "
        "ON tasks (tenant_id, status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tasks_tenant_created "
        "ON tasks (tenant_id, created_at DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agents_status ON agents (status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agents_swarm_status ON agents (swarm_id, status) "
        "WHERE swarm_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenant_audit_logs_tenant_created "
        "ON tenant_audit_logs (tenant_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tenant_audit_logs_tenant_created")
    op.execute("DROP INDEX IF EXISTS ix_agents_swarm_status")
    op.execute("DROP INDEX IF EXISTS ix_agents_status")
    op.execute("DROP INDEX IF EXISTS ix_tasks_tenant_created")
    op.execute("DROP INDEX IF EXISTS ix_tasks_tenant_status_created")
