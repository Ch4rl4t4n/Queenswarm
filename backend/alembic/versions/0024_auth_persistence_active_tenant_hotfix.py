"""Hotfix: ensure dashboard_users.active_tenant_id exists for auth persistence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0024_auth_persistence_active_tenant_hotfix"
down_revision = "0023_browser_harness_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing active_tenant_id column/index/fk when drifted environments skipped it."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {col["name"] for col in inspector.get_columns("dashboard_users")}
    if "active_tenant_id" not in existing_columns:
        op.add_column("dashboard_users", sa.Column("active_tenant_id", postgresql.UUID(as_uuid=True), nullable=True))

    # Re-inspect after possible column creation.
    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("dashboard_users")}
    if "ix_dashboard_users_active_tenant_id" not in existing_indexes:
        op.create_index(
            "ix_dashboard_users_active_tenant_id",
            "dashboard_users",
            ["active_tenant_id"],
            unique=False,
        )

    existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("dashboard_users")}
    if "fk_dashboard_users_active_tenant_id" not in existing_fks:
        op.create_foreign_key(
            "fk_dashboard_users_active_tenant_id",
            "dashboard_users",
            "tenants",
            ["active_tenant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """No-op downgrade for emergency drift repair migration."""

    # Intentionally left as no-op to avoid dropping live tenancy references.
    return
