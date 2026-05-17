"""Phase 2.5 — Universal External Project Integration registry + audit."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_external_projects"
down_revision = "0014_dynamic_connectors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_projects",
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
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("project_kind", sa.String(length=32), nullable=False),
        sa.Column("owner_dashboard_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("webhook_secret_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_dashboard_user_id"],
            ["dashboard_users.id"],
            name="fk_external_projects_owner_dashboard_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_external_projects_slug"),
    )
    op.create_index("ix_external_projects_slug", "external_projects", ["slug"], unique=False)
    op.create_index(
        "ix_external_projects_project_kind",
        "external_projects",
        ["project_kind"],
        unique=False,
    )
    op.create_index(
        "ix_external_projects_owner_dashboard_user_id",
        "external_projects",
        ["owner_dashboard_user_id"],
        unique=False,
    )

    op.create_table(
        "external_project_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[\"run\"]'::jsonb"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["external_projects.id"],
            name="fk_external_project_api_keys_project_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_project_api_keys_project_id",
        "external_project_api_keys",
        ["project_id"],
        unique=False,
    )

    op.create_table(
        "external_project_run_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_slug", sa.String(length=160), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), server_default="0", nullable=False),
        sa.Column(
            "human_approval_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("human_approved", sa.Boolean(), nullable=True),
        sa.Column("payload_excerpt", sa.Text(), server_default="''", nullable=False),
        sa.Column(
            "result_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["api_key_id"],
            ["external_project_api_keys.id"],
            name="fk_external_project_run_audit_api_key_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["external_projects.id"],
            name="fk_external_project_run_audit_project_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_project_run_audit_created_at",
        "external_project_run_audit",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_project_run_audit_project_id",
        "external_project_run_audit",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_external_project_run_audit_api_key_id",
        "external_project_run_audit",
        ["api_key_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_external_project_run_audit_api_key_id", table_name="external_project_run_audit")
    op.drop_index("ix_external_project_run_audit_project_id", table_name="external_project_run_audit")
    op.drop_index("ix_external_project_run_audit_created_at", table_name="external_project_run_audit")
    op.drop_table("external_project_run_audit")
    op.drop_index("ix_external_project_api_keys_project_id", table_name="external_project_api_keys")
    op.drop_table("external_project_api_keys")
    op.drop_index("ix_external_projects_owner_dashboard_user_id", table_name="external_projects")
    op.drop_index("ix_external_projects_project_kind", table_name="external_projects")
    op.drop_index("ix_external_projects_slug", table_name="external_projects")
    op.drop_table("external_projects")
