"""Agent config rows backing UI-defined universal executor bees."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0005_agent_configs_dynamic_factory"
down_revision = "0004_dashboard_prefs_api_keys"
branch_labels = None
depends_on = None

UUID = pg.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "agent_configs",
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
        sa.Column("agent_id", UUID, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=True),
        sa.Column(
            "tools",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("output_format", sa.String(length=50), nullable=False, server_default="text"),
        sa.Column("output_destination", sa.String(length=200), nullable=False, server_default="dashboard"),
        sa.Column(
            "output_config",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("schedule_type", sa.String(length=50), nullable=False, server_default="on_demand"),
        sa.Column("schedule_value", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_result", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("agent_id", name="uq_agent_configs_agent_id"),
    )


def downgrade() -> None:
    op.drop_table("agent_configs")