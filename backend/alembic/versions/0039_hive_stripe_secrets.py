"""Alembic migration: encrypted Stripe platform secrets vault."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039_hive_stripe_secrets"
down_revision = "0038_pending_review_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hive_stripe_secrets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("secret_key_ciphertext", sa.Text(), nullable=True),
        sa.Column("webhook_secret_ciphertext", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("hive_stripe_secrets")
