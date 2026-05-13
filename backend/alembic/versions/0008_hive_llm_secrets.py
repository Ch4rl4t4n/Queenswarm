"""Encrypted LLM provider secrets overridable from dashboard (vault)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_hive_llm_secrets"
down_revision = "0007_external_outputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hive_llm_secrets",
        sa.Column("provider", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("hive_llm_secrets")
