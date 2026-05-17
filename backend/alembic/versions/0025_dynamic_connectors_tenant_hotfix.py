"""Hotfix: ensure dynamic_connectors.tenant_id exists for tenant-scoped RBAC."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0025_dynamic_connectors_tenant_hotfix"
down_revision = "0024_auth_persistence_active_tenant_hotfix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing tenant scope column/index/fk on drifted environments."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {col["name"] for col in inspector.get_columns("dynamic_connectors")}
    if "tenant_id" not in existing_columns:
        op.add_column("dynamic_connectors", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))

    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("dynamic_connectors")}
    if "ix_dynamic_connectors_tenant_id" not in existing_indexes:
        op.create_index(
            "ix_dynamic_connectors_tenant_id",
            "dynamic_connectors",
            ["tenant_id"],
            unique=False,
        )

    existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("dynamic_connectors")}
    if "fk_dynamic_connectors_tenant_id" not in existing_fks:
        op.create_foreign_key(
            "fk_dynamic_connectors_tenant_id",
            "dynamic_connectors",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """No-op downgrade for emergency drift repair migration."""

    return
