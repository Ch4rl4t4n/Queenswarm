"""Dashboard user preferences + persisted API keys for Bearer scripts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0004_dashboard_prefs_api_keys"
down_revision = "0003_dashboard_users"
branch_labels = None
depends_on = None

UUID = pg.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("dashboard_users", sa.Column("timezone", sa.String(length=96), nullable=True))
    op.add_column(
        "dashboard_users",
        sa.Column(
            "notification_prefs",
            pg.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_table(
        "dashboard_api_keys",
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
        sa.Column("user_id", UUID, sa.ForeignKey("dashboard_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dashboard_api_keys_user_id", "dashboard_api_keys", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dashboard_api_keys_user_id", table_name="dashboard_api_keys")
    op.drop_table("dashboard_api_keys")
    op.drop_column("dashboard_users", "notification_prefs")
    op.drop_column("dashboard_users", "timezone")
