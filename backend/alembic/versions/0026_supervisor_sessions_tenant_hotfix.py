"""Hotfix: ensure supervisor_sessions.tenant_id exists for tenant-scoped queries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0026_supervisor_sessions_tenant_hotfix"
down_revision = "0025_dynamic_connectors_tenant_hotfix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing tenant scope column/index/fk on drifted environments."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {col["name"] for col in inspector.get_columns("supervisor_sessions")}
    if "tenant_id" not in existing_columns:
        op.add_column("supervisor_sessions", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))

    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("supervisor_sessions")}
    if "ix_supervisor_sessions_tenant_id" not in existing_indexes:
        op.create_index(
            "ix_supervisor_sessions_tenant_id",
            "supervisor_sessions",
            ["tenant_id"],
            unique=False,
        )

    existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("supervisor_sessions")}
    if "fk_supervisor_sessions_tenant_id" not in existing_fks:
        op.create_foreign_key(
            "fk_supervisor_sessions_tenant_id",
            "supervisor_sessions",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """No-op downgrade for emergency drift repair migration."""

    return
