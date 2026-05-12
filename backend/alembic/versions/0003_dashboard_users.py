"""Dashboard operator identities for password + TOTP login."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0003_dashboard_users"
down_revision = "0002_hive_async_workflow_runs"
branch_labels = None
depends_on = None

UUID = pg.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "dashboard_users",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("totp_secret", sa.Text(), nullable=True),
        sa.Column("totp_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("totp_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("email", name="uq_dashboard_users_email"),
    )
    op.create_index("ix_dashboard_users_email", "dashboard_users", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dashboard_users_email", table_name="dashboard_users")
    op.drop_table("dashboard_users")
