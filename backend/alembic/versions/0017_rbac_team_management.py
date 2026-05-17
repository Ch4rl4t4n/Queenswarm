"""Phase 10.2 — RBAC team management (invites + audit logs)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017_rbac_team_management"
down_revision = "0016_multi_tenancy_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invite_token", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["dashboard_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_token", name="uq_tenant_invites_invite_token"),
    )
    op.create_index("ix_tenant_invites_tenant_id", "tenant_invites", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_invites_email", "tenant_invites", ["email"], unique=False)
    op.create_index("ix_tenant_invites_invite_token", "tenant_invites", ["invite_token"], unique=False)

    op.create_table(
        "tenant_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["dashboard_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_audit_logs_tenant_id", "tenant_audit_logs", ["tenant_id"], unique=False)
    op.create_index("ix_tenant_audit_logs_actor_user_id", "tenant_audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_tenant_audit_logs_action", "tenant_audit_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenant_audit_logs_action", table_name="tenant_audit_logs")
    op.drop_index("ix_tenant_audit_logs_actor_user_id", table_name="tenant_audit_logs")
    op.drop_index("ix_tenant_audit_logs_tenant_id", table_name="tenant_audit_logs")
    op.drop_table("tenant_audit_logs")

    op.drop_index("ix_tenant_invites_invite_token", table_name="tenant_invites")
    op.drop_index("ix_tenant_invites_email", table_name="tenant_invites")
    op.drop_index("ix_tenant_invites_tenant_id", table_name="tenant_invites")
    op.drop_table("tenant_invites")
