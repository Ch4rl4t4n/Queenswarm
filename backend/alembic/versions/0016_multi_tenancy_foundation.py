"""Phase 10.1 — multi-tenancy foundation (tenant + scoped entity columns)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_multi_tenancy_foundation"
down_revision = "0015_external_projects"
branch_labels = None
depends_on = None


def _add_tenant_column(table_name: str) -> None:
    op.add_column(table_name, sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"], unique=False)
    op.create_foreign_key(
        f"fk_{table_name}_tenant_id",
        table_name,
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def upgrade() -> None:
    op.create_table(
        "tenants",
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
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=False)

    op.create_table(
        "dashboard_user_tenants",
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
        sa.Column("dashboard_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dashboard_user_id"], ["dashboard_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dashboard_user_id",
            "tenant_id",
            name="uq_dashboard_user_tenant_membership",
        ),
    )
    op.create_index(
        "ix_dashboard_user_tenants_dashboard_user_id",
        "dashboard_user_tenants",
        ["dashboard_user_id"],
        unique=False,
    )
    op.create_index("ix_dashboard_user_tenants_tenant_id", "dashboard_user_tenants", ["tenant_id"], unique=False)

    op.add_column("dashboard_users", sa.Column("active_tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_dashboard_users_active_tenant_id", "dashboard_users", ["active_tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_dashboard_users_active_tenant_id",
        "dashboard_users",
        "tenants",
        ["active_tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for table_name in (
        "tasks",
        "supervisor_sessions",
        "sub_agent_sessions",
        "supervisor_session_events",
        "supervisor_routines",
        "knowledge_items",
        "learning_logs",
        "external_outputs",
        "dynamic_connectors",
        "external_projects",
        "external_project_api_keys",
        "external_project_run_audit",
        "connector_vault_entries",
    ):
        _add_tenant_column(table_name)


def downgrade() -> None:
    for table_name in (
        "connector_vault_entries",
        "external_project_run_audit",
        "external_project_api_keys",
        "external_projects",
        "dynamic_connectors",
        "external_outputs",
        "learning_logs",
        "knowledge_items",
        "supervisor_routines",
        "supervisor_session_events",
        "sub_agent_sessions",
        "supervisor_sessions",
        "tasks",
    ):
        op.drop_constraint(f"fk_{table_name}_tenant_id", table_name, type_="foreignkey")
        op.drop_index(f"ix_{table_name}_tenant_id", table_name=table_name)
        op.drop_column(table_name, "tenant_id")

    op.drop_constraint("fk_dashboard_users_active_tenant_id", "dashboard_users", type_="foreignkey")
    op.drop_index("ix_dashboard_users_active_tenant_id", table_name="dashboard_users")
    op.drop_column("dashboard_users", "active_tenant_id")

    op.drop_index("ix_dashboard_user_tenants_tenant_id", table_name="dashboard_user_tenants")
    op.drop_index("ix_dashboard_user_tenants_dashboard_user_id", table_name="dashboard_user_tenants")
    op.drop_table("dashboard_user_tenants")

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
